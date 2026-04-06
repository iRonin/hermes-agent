"""Tests for PR #4833: feat/per-skill-model-routing

Verifies that delegate_task() accepts model/provider/skill/skills params,
that skill SKILL.md frontmatter model: field drives subagent model selection,
and that per-task models override call-level models in batch mode.
"""

import json
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.delegate_tool import (
    delegate_task,
    _load_skill_for_subagent,
    _resolve_delegation_credentials,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parent(depth=0, model="anthropic/claude-sonnet-4", provider="openrouter"):
    p = MagicMock()
    p.base_url = "https://openrouter.ai/api/v1"
    p.api_key = "sk-test"
    p.provider = provider
    p.api_mode = "chat_completions"
    p.model = model
    p.platform = "cli"
    p.providers_allowed = None
    p.providers_ignored = None
    p.providers_order = None
    p.provider_sort = None
    p._session_db = None
    p._delegate_depth = depth
    p._active_children = []
    p._active_children_lock = threading.Lock()
    p._print_fn = None
    p.tool_progress_callback = None
    p.thinking_callback = None
    p.enabled_toolsets = ["terminal", "file"]
    p.max_tokens = None
    p.reasoning_config = None
    p.prefill_messages = None
    p.session_id = "parent-session-id"
    p._memory_manager = None
    return p


MOCK_CHILD_RESULT = {
    "task_index": 0,
    "status": "completed",
    "summary": "Done",
    "api_calls": 1,
    "duration_seconds": 1.0,
}


# ---------------------------------------------------------------------------
# Test: explicit model= is passed to child agent
# ---------------------------------------------------------------------------

class TestExplicitModelParam:

    @patch("tools.delegate_tool._run_single_child")
    @patch("tools.delegate_tool._build_child_agent")
    @patch("tools.delegate_tool._load_config", return_value={})
    def test_explicit_model_passed_to_child(self, mock_cfg, mock_build, mock_run):
        """delegate_task(model='fast-model') must build child with that model."""
        mock_build.return_value = MagicMock()
        mock_run.return_value = MOCK_CHILD_RESULT

        parent = _make_parent()
        delegate_task(goal="do thing", model="google/gemini-flash-1.5", parent_agent=parent)

        # _build_child_agent must be called with the explicit model
        _, kwargs = mock_build.call_args
        assert kwargs.get("model") == "google/gemini-flash-1.5", (
            "explicit model= must be forwarded to _build_child_agent"
        )

    @patch("tools.delegate_tool._run_single_child")
    @patch("tools.delegate_tool._build_child_agent")
    @patch("tools.delegate_tool._load_config", return_value={})
    def test_no_model_falls_back_to_parent(self, mock_cfg, mock_build, mock_run):
        """When no model given, child inherits parent's model."""
        mock_build.return_value = MagicMock()
        mock_run.return_value = MOCK_CHILD_RESULT

        parent = _make_parent(model="anthropic/claude-opus-4")
        delegate_task(goal="do thing", parent_agent=parent)

        _, kwargs = mock_build.call_args
        # With no override, creds["model"] is None (no config), so child uses parent's model
        # _build_child_agent will get model=None which then falls to parent_agent.model
        assert kwargs.get("model") is None or kwargs.get("model") == "anthropic/claude-opus-4"


# ---------------------------------------------------------------------------
# Test: skill frontmatter model: is used as child model
# ---------------------------------------------------------------------------

class TestSkillFrontmatterModel:

    @patch("tools.delegate_tool._run_single_child")
    @patch("tools.delegate_tool._build_child_agent")
    @patch("tools.delegate_tool._load_config", return_value={})
    @patch("tools.delegate_tool._load_skill_for_subagent")
    def test_skill_frontmatter_model_used(self, mock_load_skill, mock_cfg, mock_build, mock_run):
        """Skill SKILL.md frontmatter model: field drives subagent model."""
        mock_load_skill.return_value = {
            "name": "coding-skill",
            "model": "anthropic/claude-opus-4",
            "provider": None,
            "content": "You are a coding expert.",
        }
        mock_build.return_value = MagicMock()
        mock_run.return_value = MOCK_CHILD_RESULT

        parent = _make_parent()
        delegate_task(goal="write code", skill="coding-skill", parent_agent=parent)

        _, kwargs = mock_build.call_args
        assert kwargs.get("model") == "anthropic/claude-opus-4", (
            "skill frontmatter model must be forwarded to child"
        )

    @patch("tools.delegate_tool._run_single_child")
    @patch("tools.delegate_tool._build_child_agent")
    @patch("tools.delegate_tool._load_config", return_value={})
    @patch("tools.delegate_tool._load_skill_for_subagent")
    def test_explicit_model_overrides_skill_frontmatter(self, mock_load_skill, mock_cfg, mock_build, mock_run):
        """Explicit model= takes priority over skill frontmatter model."""
        mock_load_skill.return_value = {
            "name": "coding-skill",
            "model": "anthropic/claude-opus-4",
            "provider": None,
            "content": "You are a coding expert.",
        }
        mock_build.return_value = MagicMock()
        mock_run.return_value = MOCK_CHILD_RESULT

        parent = _make_parent()
        delegate_task(
            goal="write code",
            model="google/gemini-flash-1.5",
            skill="coding-skill",
            parent_agent=parent,
        )

        _, kwargs = mock_build.call_args
        # explicit model wins over skill frontmatter
        assert kwargs.get("model") == "google/gemini-flash-1.5"


# ---------------------------------------------------------------------------
# Test: per-task model overrides in batch mode
# ---------------------------------------------------------------------------

class TestPerTaskModelBatch:

    @patch("tools.delegate_tool._run_single_child")
    @patch("tools.delegate_tool._build_child_agent")
    @patch("tools.delegate_tool._load_config", return_value={})
    def test_per_task_model_overrides_call_level(self, mock_cfg, mock_build, mock_run):
        """Per-task model in tasks[] overrides the call-level model."""
        built_children = []

        def capture_build(**kwargs):
            child = MagicMock()
            built_children.append(kwargs.get("model"))
            return child

        mock_build.side_effect = capture_build
        mock_run.side_effect = [
            {"task_index": 0, "status": "completed", "summary": "A", "api_calls": 1, "duration_seconds": 1.0},
            {"task_index": 1, "status": "completed", "summary": "B", "api_calls": 1, "duration_seconds": 1.0},
        ]

        parent = _make_parent()
        tasks = [
            {"goal": "task A", "model": "google/gemini-flash-1.5"},
            {"goal": "task B"},  # no per-task model → falls back to call-level
        ]
        delegate_task(tasks=tasks, model="anthropic/claude-haiku", parent_agent=parent)

        # task A should use per-task model
        assert built_children[0] == "google/gemini-flash-1.5"
        # task B should use call-level model
        assert built_children[1] == "anthropic/claude-haiku"


# ---------------------------------------------------------------------------
# Test: delegation config fallback
# ---------------------------------------------------------------------------

class TestDelegationConfigFallback:

    @patch("tools.delegate_tool._run_single_child")
    @patch("tools.delegate_tool._build_child_agent")
    @patch("tools.delegate_tool._load_config")
    def test_delegation_config_model_used_when_no_override(self, mock_cfg, mock_build, mock_run):
        """When no call-level model, delegation.model from config is used."""
        mock_cfg.return_value = {"model": "openai/gpt-4-turbo"}
        mock_build.return_value = MagicMock()
        mock_run.return_value = MOCK_CHILD_RESULT

        parent = _make_parent()
        delegate_task(goal="do thing", parent_agent=parent)

        _, kwargs = mock_build.call_args
        assert kwargs.get("model") == "openai/gpt-4-turbo", (
            "delegation.model from config must be used when no explicit model given"
        )

    @patch("tools.delegate_tool._run_single_child")
    @patch("tools.delegate_tool._build_child_agent")
    @patch("tools.delegate_tool._load_config")
    def test_explicit_model_overrides_config(self, mock_cfg, mock_build, mock_run):
        """Explicit model= parameter takes priority over delegation config."""
        mock_cfg.return_value = {"model": "openai/gpt-4-turbo"}
        mock_build.return_value = MagicMock()
        mock_run.return_value = MOCK_CHILD_RESULT

        parent = _make_parent()
        delegate_task(goal="do thing", model="google/gemini-flash-1.5", parent_agent=parent)

        _, kwargs = mock_build.call_args
        assert kwargs.get("model") == "google/gemini-flash-1.5"


# ---------------------------------------------------------------------------
# Test: skill= and skills= load skill content into system prompt
# ---------------------------------------------------------------------------

class TestSkillContentInjection:

    @patch("tools.delegate_tool._run_single_child")
    @patch("tools.delegate_tool._build_child_agent")
    @patch("tools.delegate_tool._load_config", return_value={})
    @patch("tools.delegate_tool._load_skill_for_subagent")
    def test_skill_content_in_system_prompt(self, mock_load_skill, mock_cfg, mock_build, mock_run):
        """skill= param injects skill body into child's system prompt via context."""
        skill_body = "Always use type hints in Python."
        mock_load_skill.return_value = {
            "name": "python-best-practices",
            "model": None,
            "provider": None,
            "content": skill_body,
        }
        mock_build.return_value = MagicMock()
        mock_run.return_value = MOCK_CHILD_RESULT

        parent = _make_parent()
        delegate_task(goal="write code", skill="python-best-practices", parent_agent=parent)

        _, kwargs = mock_build.call_args
        context = kwargs.get("context") or ""
        assert skill_body in context, (
            "skill content must appear in child context/system prompt"
        )

    @patch("tools.delegate_tool._run_single_child")
    @patch("tools.delegate_tool._build_child_agent")
    @patch("tools.delegate_tool._load_config", return_value={})
    @patch("tools.delegate_tool._load_skill_for_subagent")
    def test_skills_multiple_loaded(self, mock_load_skill, mock_cfg, mock_build, mock_run):
        """skills= param loads multiple skills into child context."""
        def skill_side_effect(name):
            return {
                "name": name,
                "model": None,
                "provider": None,
                "content": f"Content of {name}",
            }
        mock_load_skill.side_effect = skill_side_effect
        mock_build.return_value = MagicMock()
        mock_run.return_value = MOCK_CHILD_RESULT

        parent = _make_parent()
        delegate_task(
            goal="do work",
            skills=["skill-alpha", "skill-beta"],
            parent_agent=parent,
        )

        _, kwargs = mock_build.call_args
        context = kwargs.get("context") or ""
        assert "Content of skill-alpha" in context
        assert "Content of skill-beta" in context


# ---------------------------------------------------------------------------
# Test: _load_skill_for_subagent unit tests
# ---------------------------------------------------------------------------

class TestLoadSkillForSubagent:

    def test_returns_empty_dict_when_skill_not_found(self, tmp_path, monkeypatch):
        """Returns {} when skill directory/file doesn't exist."""
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        with patch("tools.delegate_tool._load_skill_for_subagent.__wrapped__"
                   if hasattr(_load_skill_for_subagent, "__wrapped__") else
                   "agent.skill_utils.get_all_skills_dirs", return_value=[tmp_path]):
            result = _load_skill_for_subagent("nonexistent-skill")
        assert result == {}

    def test_reads_frontmatter_model_from_skill_md(self, tmp_path):
        """Reads model: field from SKILL.md frontmatter."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nmodel: anthropic/claude-opus-4\n---\n\nSkill body text.\n"
        )

        with patch("agent.skill_utils.get_all_skills_dirs", return_value=[tmp_path]):
            result = _load_skill_for_subagent("my-skill")

        assert result.get("model") == "anthropic/claude-opus-4"
        assert "Skill body text." in result.get("content", "")

    def test_reads_skill_without_model_frontmatter(self, tmp_path):
        """Skills without model: in frontmatter return model=None."""
        skill_dir = tmp_path / "plain-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ntitle: Plain Skill\n---\n\nJust instructions.\n"
        )

        with patch("agent.skill_utils.get_all_skills_dirs", return_value=[tmp_path]):
            result = _load_skill_for_subagent("plain-skill")

        assert result.get("model") is None
        assert result.get("name") == "plain-skill"


# ---------------------------------------------------------------------------
# Test: _resolve_delegation_credentials with override params
# ---------------------------------------------------------------------------

class TestResolveDelegationCredentials:

    def test_override_model_takes_priority_over_config(self):
        """override_model param takes priority over delegation.model config."""
        cfg = {"model": "config-model"}
        parent = _make_parent()
        result = _resolve_delegation_credentials(cfg, parent, override_model="explicit-model")
        assert result["model"] == "explicit-model"

    def test_config_model_used_when_no_override(self):
        """delegation.model from config is used when no override given."""
        cfg = {"model": "config-model"}
        parent = _make_parent()
        result = _resolve_delegation_credentials(cfg, parent)
        assert result["model"] == "config-model"

    def test_none_model_when_no_config_no_override(self):
        """model is None when neither config nor override provide it."""
        cfg = {}
        parent = _make_parent()
        result = _resolve_delegation_credentials(cfg, parent)
        assert result["model"] is None

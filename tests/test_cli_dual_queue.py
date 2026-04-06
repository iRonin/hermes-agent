"""Tests for dual-queue / dispatch-mode attributes on HermesCLI.

Covers feat/dual-queue-v2 attributes:
  - steering_dispatch
  - followup_dispatch
  - busy_input_mode
  - _steering_queue
  - _cancelled_steerings
  - _steering_recall_count
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_cli(env_overrides=None, config_overrides=None, **kwargs):
    """Create a HermesCLI instance with minimal mocking."""
    import importlib

    _clean_config = {
        "model": {
            "default": "anthropic/claude-opus-4.6",
            "base_url": "https://openrouter.ai/api/v1",
            "provider": "auto",
        },
        "display": {"compact": False, "tool_progress": "all"},
        "agent": {},
        "terminal": {"env_type": "local"},
    }
    if config_overrides:
        _clean_config.update(config_overrides)
    clean_env = {"LLM_MODEL": "", "HERMES_MAX_ITERATIONS": ""}
    if env_overrides:
        clean_env.update(env_overrides)
    prompt_toolkit_stubs = {
        "prompt_toolkit": MagicMock(),
        "prompt_toolkit.history": MagicMock(),
        "prompt_toolkit.styles": MagicMock(),
        "prompt_toolkit.patch_stdout": MagicMock(),
        "prompt_toolkit.application": MagicMock(),
        "prompt_toolkit.layout": MagicMock(),
        "prompt_toolkit.layout.processors": MagicMock(),
        "prompt_toolkit.filters": MagicMock(),
        "prompt_toolkit.layout.dimension": MagicMock(),
        "prompt_toolkit.layout.menus": MagicMock(),
        "prompt_toolkit.widgets": MagicMock(),
        "prompt_toolkit.key_binding": MagicMock(),
        "prompt_toolkit.completion": MagicMock(),
        "prompt_toolkit.formatted_text": MagicMock(),
        "prompt_toolkit.auto_suggest": MagicMock(),
    }
    with patch.dict(sys.modules, prompt_toolkit_stubs), \
         patch.dict("os.environ", clean_env, clear=False):
        import cli as _cli_mod
        _cli_mod = importlib.reload(_cli_mod)
        with patch.object(_cli_mod, "get_tool_definitions", return_value=[]), \
             patch.dict(_cli_mod.__dict__, {"CLI_CONFIG": _clean_config}):
            return _cli_mod.HermesCLI(**kwargs)


class TestSteeringDispatch:
    """steering_dispatch reads CLI_CONFIG['display']['steering_dispatch'], default 'one_by_one'."""

    def test_default_steering_dispatch_is_one_by_one(self):
        cli = _make_cli()
        assert cli.steering_dispatch == "one_by_one"

    def test_steering_dispatch_config_all_at_once(self):
        cli = _make_cli(config_overrides={"display": {"steering_dispatch": "all_at_once"}})
        assert cli.steering_dispatch == "all_at_once"


class TestFollowupDispatch:
    """followup_dispatch reads CLI_CONFIG['display']['followup_dispatch'], default 'one_by_one'."""

    def test_default_followup_dispatch_is_one_by_one(self):
        cli = _make_cli()
        assert cli.followup_dispatch == "one_by_one"

    def test_followup_dispatch_config_all_at_once(self):
        cli = _make_cli(config_overrides={"display": {"followup_dispatch": "all_at_once"}})
        assert cli.followup_dispatch == "all_at_once"


class TestBusyInputModeDispatch:
    """busy_input_mode reads CLI_CONFIG['display']['busy_input_mode'], default 'interrupt'."""

    def test_default_busy_input_mode_is_interrupt(self):
        cli = _make_cli()
        assert cli.busy_input_mode == "interrupt"

    def test_busy_input_mode_config_queue(self):
        cli = _make_cli(config_overrides={"display": {"busy_input_mode": "queue"}})
        assert cli.busy_input_mode == "queue"


class TestSteeringQueueState:
    """_steering_queue, _cancelled_steerings, _steering_recall_count initial state."""

    def test_steering_queue_is_list(self):
        cli = _make_cli()
        assert isinstance(cli._steering_queue, list)

    def test_steering_queue_starts_empty(self):
        cli = _make_cli()
        assert cli._steering_queue == []

    def test_cancelled_steerings_is_set(self):
        cli = _make_cli()
        assert isinstance(cli._cancelled_steerings, set)

    def test_cancelled_steerings_starts_empty(self):
        cli = _make_cli()
        assert len(cli._cancelled_steerings) == 0

    def test_steering_recall_count_is_zero(self):
        cli = _make_cli()
        assert cli._steering_recall_count == 0

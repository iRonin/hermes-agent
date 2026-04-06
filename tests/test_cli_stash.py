"""Tests for input-stash attributes on HermesCLI.

Covers feat/input-stash-extended attributes:
  - _stash_list        (list, was _stashed_input before)
  - _stash_panel_open  (bool)
  - _stash_panel_cursor (int)
  - stash_auto_restore  (bool, from CLI_CONFIG)
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


class TestStashList:
    """_stash_list is a list (not None), replacing the old _stashed_input attribute."""

    def test_stash_list_is_list(self):
        cli = _make_cli()
        assert isinstance(cli._stash_list, list)

    def test_stash_list_starts_empty(self):
        cli = _make_cli()
        assert cli._stash_list == []

    def test_no_stashed_input_attribute(self):
        """Old _stashed_input attribute must not exist (it was removed)."""
        cli = _make_cli()
        assert not hasattr(cli, "_stashed_input")

    def test_stash_list_is_independent_between_instances(self):
        """Each CLI instance gets its own list — no shared mutable default."""
        cli_a = _make_cli()
        cli_b = _make_cli()
        cli_a._stash_list.append("hello")
        assert cli_b._stash_list == [], (
            "_stash_list should not be shared between instances"
        )


class TestStashPanelState:
    """_stash_panel_open and _stash_panel_cursor initial values."""

    def test_stash_panel_open_is_false(self):
        cli = _make_cli()
        assert cli._stash_panel_open is False

    def test_stash_panel_cursor_is_zero(self):
        cli = _make_cli()
        assert cli._stash_panel_cursor == 0


class TestStashAutoRestore:
    """stash_auto_restore reads CLI_CONFIG['display']['stash_auto_restore'], default False."""

    def test_default_stash_auto_restore_is_false(self):
        cli = _make_cli()
        assert cli.stash_auto_restore is False

    def test_stash_auto_restore_config_true(self):
        cli = _make_cli(config_overrides={"display": {"stash_auto_restore": True}})
        assert cli.stash_auto_restore is True

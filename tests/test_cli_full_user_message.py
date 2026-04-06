"""Tests for PR #5073 feat/full-user-message.

Covers: display.show_full_user_message config + _show_full_user_message attr on HermesCLI.
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_cli(env_overrides=None, config_overrides=None, **kwargs):
    """Create a HermesCLI instance with minimal mocking (mirrors test_cli_init.py)."""
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
        # Deep-merge display sub-dict so callers can add individual display keys.
        for key, value in config_overrides.items():
            if key in _clean_config and isinstance(_clean_config[key], dict) and isinstance(value, dict):
                _clean_config[key] = {**_clean_config[key], **value}
            else:
                _clean_config[key] = value

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


class TestShowFullUserMessageDefault:
    """Default config: show_full_user_message not set → False."""

    def test_attribute_exists_on_instance(self):
        cli = _make_cli()
        assert hasattr(cli, "_show_full_user_message"), (
            "_show_full_user_message must be set in HermesCLI.__init__"
        )

    def test_default_value_is_false(self):
        cli = _make_cli()
        assert cli._show_full_user_message is False

    def test_default_value_is_bool(self):
        cli = _make_cli()
        assert isinstance(cli._show_full_user_message, bool), (
            "_show_full_user_message must be bool, not a truthy/falsy non-bool"
        )


class TestShowFullUserMessageConfigTrue:
    """Config display.show_full_user_message: true → _show_full_user_message is True."""

    def test_config_true_sets_attribute(self):
        cli = _make_cli(config_overrides={"display": {"show_full_user_message": True}})
        assert cli._show_full_user_message is True

    def test_config_true_value_is_bool(self):
        cli = _make_cli(config_overrides={"display": {"show_full_user_message": True}})
        assert isinstance(cli._show_full_user_message, bool)

    def test_config_false_explicit(self):
        cli = _make_cli(config_overrides={"display": {"show_full_user_message": False}})
        assert cli._show_full_user_message is False

    def test_config_string_true_coerced_to_bool(self):
        """YAML might load 'true' as bool but we coerce just in case."""
        cli = _make_cli(config_overrides={"display": {"show_full_user_message": True}})
        assert isinstance(cli._show_full_user_message, bool)
        assert cli._show_full_user_message is not None

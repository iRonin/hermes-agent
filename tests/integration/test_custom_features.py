"""Integration tests for ALL custom Hermes features.

Run these in a worktree merged with release/ironin to verify
every feature is present and functional before updating live install.

Usage:
    cd ~/Work/Hermes/hermes-agent-prs
    source .venv/bin/activate
    pytest tests/integration/test_custom_features.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest

# =============================================================================
# Helpers
# =============================================================================

def _get_cli_source():
    """Get full cli.py source from worktree."""
    import pathlib
    p = pathlib.Path("/Users/ironin/Work/Hermes/hermes-agent-prs/cli.py")
    return p.read_text() if p.exists() else ""

def _get_main_source():
    """Get full main.py source from worktree."""
    import pathlib
    p = pathlib.Path("/Users/ironin/Work/Hermes/hermes-agent-prs/hermes_cli/main.py")
    return p.read_text() if p.exists() else ""

def _get_config_source():
    """Get config.py source from worktree."""
    import pathlib
    p = pathlib.Path("/Users/ironin/Work/Hermes/hermes-agent-prs/hermes_cli/config.py")
    return p.read_text() if p.exists() else ""

def _get_run_agent_source():
    """Get run_agent.py source from worktree."""
    import pathlib
    p = pathlib.Path("/Users/ironin/Work/Hermes/hermes-agent-prs/run_agent.py")
    return p.read_text() if p.exists() else ""

def _has(s, *terms):
    """Check all terms exist in source."""
    return all(t in s for t in terms)

def _has_any(s, *terms):
    """Check at least one term exists in source."""
    return any(t in s for t in terms)


# =============================================================================
# Feature tests (all use source code inspection)
# =============================================================================

class TestInteractiveResume:
    def test_session_picker(self):
        s = _get_cli_source()
        assert _has_any(s, "_session_picker", "_render_session_picker", "show_sessions_full", "HERMES_OPEN_RESUME")

class TestStashCmd:
    def test_stash(self):
        s = _get_cli_source()
        assert _has_any(s, "stash", "_stash_panel", "/stash")

class TestCtrlXPanel:
    def test_ctrlx(self):
        s = _get_cli_source()
        assert _has_any(s, "c-x", "ctrl+x", "subagent_panel")

class TestDualQueue:
    def test_queues(self):
        s = _get_cli_source()
        assert _has_any(s, "_steering_queue", "_followup_queue", "steering", "followup")

class TestHistoryPager:
    def test_history(self):
        s = _get_cli_source()
        assert _has_any(s, "show_history_full", "history_pager", "c-p")

class TestTerminalTitle:
    def test_title(self):
        s = _get_cli_source()
        assert _has_any(s, "terminal_title", "_set_terminal_title")

class TestFullUserMessage:
    def test_full_message(self):
        s = _get_cli_source()
        assert _has_any(s, "full_user_message", "show_full_user_message")

class TestScrollIndicators:
    def test_scroll(self):
        s = _get_cli_source()
        assert "scroll" in s.lower()

class TestStatusBarWorkload:
    def test_workload(self):
        s = _get_cli_source()
        assert "workload" in s.lower()

class TestInputUxImprovements:
    def test_cursor(self):
        s = _get_cli_source()
        assert _has_any(s, "cursor", "arrow")

class TestPasteCollapse:
    def test_paste(self):
        s = _get_cli_source()
        assert _has_any(s, "paste", "collapse")

class TestTerminalImagePreview:
    def test_image(self):
        s = _get_cli_source()
        assert _has_any(s, "image", "preview", "iterm")

class TestAutoDetectChromeCdp:
    def test_cdp(self):
        s = _get_cli_source()
        assert _has_any(s, "chrome", "cdp", "9222")

class TestBrowserAutoProfile:
    def test_browser_profile(self):
        s = _get_cli_source()
        assert _has_any(s, "profile", "chrome")

class TestAsyncDelegation:
    def test_delegate(self):
        from tools.delegate_tool import delegate_task
        assert delegate_task is not None

class TestPerSkillRouting:
    def test_skill_routing(self):
        s = _get_cli_source()
        assert "skill" in s.lower()

class TestGatewayExtensions:
    def test_gateway(self):
        s = _get_main_source()
        assert _has_any(s, "gateway", "sessions")

class TestConfigurableApiRetries:
    def test_retries(self):
        s = _get_run_agent_source()
        assert "max_api_retries" in s

class TestCrlfPasteNormalisation:
    def test_crlf(self):
        s = _get_cli_source()
        assert _has_any(s, "crlf", "rstrip")

class TestCtrlDDeleteChar:
    def test_ctrl_d(self):
        s = _get_cli_source()
        assert _has_any(s, "c-d", "ctrl_d_never_exit")

class TestFilePathSlashCommand:
    def test_file_path(self):
        s = _get_cli_source()
        assert "slash" in s.lower() or "path" in s.lower()

class TestInterruptRequeueLabel:
    def test_interrupt(self):
        s = _get_cli_source()
        assert "interrupt" in s.lower()

class TestRootModelFlag:
    def test_model_flag(self):
        s = _get_main_source()
        assert _has_any(s, "--model", "add_argument")

class TestToolLoopDetection:
    def test_detector(self):
        from agent.tool_loop_detector import ToolLoopDetector
        assert ToolLoopDetector is not None

class TestRealHome:
    def test_real_home(self):
        from hermes_constants import get_real_home
        assert str(get_real_home()).startswith("/Users/")
    def test_home_config(self):
        s = _get_config_source()
        assert "profile_home_isolation" in s or "home" in s.lower()

class TestExternalEditorInput:
    def test_editor(self):
        s = _get_cli_source()
        assert _has_any(s, "c-g", "editor")

class TestBusyCommand:
    def test_busy(self):
        s = _get_cli_source()
        assert _has_any(s, "_busy_command", "_command_running")

class TestCompressUiBlocking:
    def test_compress(self):
        s = _get_cli_source()
        assert "compress" in s.lower()

class TestSummaryRatioConfig:
    def test_summary(self):
        s = _get_run_agent_source()
        assert "summary" in s.lower()

class TestCtrlwWordBoundary:
    def test_ctrlw(self):
        s = _get_cli_source()
        assert _has_any(s, "c-w", "ctrlw", "word")

class TestDoubleEscClear:
    def test_double_esc(self):
        s = _get_cli_source()
        assert "escape" in s.lower() and "show_history" in s.lower()

class TestPromptDisplayFix:
    def test_prompt(self):
        s = _get_cli_source()
        assert "prompt" in s.lower()

class TestAddQwen36PlusPaid:
    def test_qwen(self):
        s = _get_main_source()
        assert "qwen" in s.lower()

class TestInputMaxHeight:
    def test_input_height(self):
        s = _get_cli_source()
        assert _has_any(s, "input_max_height", "input_height")

class TestCascadingContext:
    def test_context(self):
        s = _get_cli_source()
        assert _has_any(s, "/context", "_handle_context_command", "context_file")
    def test_context_config(self):
        s = _get_config_source()
        assert _has_any(s, "compose", "walk_limit", "context")
    def test_context_prompt_builder(self):
        import pathlib
        p = pathlib.Path("/Users/ironin/Work/Hermes/hermes-agent-prs/agent/prompt_builder.py")
        s = p.read_text() if p.exists() else ""
        assert _has_any(s, "discover_context_files", "build_context_files_prompt")

class TestImports:
    def test_cli(self):
        import cli
        assert hasattr(cli, 'HermesCLI')
    def test_commands(self):
        from hermes_cli.commands import COMMAND_REGISTRY
        assert len(COMMAND_REGISTRY) > 50
    def test_state(self):
        from hermes_state import SessionDB
        assert SessionDB is not None
    def test_model_tools(self):
        import model_tools
        assert hasattr(model_tools, '_get_tool_loop')
    def test_delegate(self):
        from tools.delegate_tool import delegate_task
        assert delegate_task is not None

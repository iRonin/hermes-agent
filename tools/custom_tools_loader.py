"""Load user-provided custom tool implementations that override built-ins.

Scans ``~/.hermes/custom_tools/`` for ``*.py`` files at startup.  Each file
whose module name (e.g. ``browser_tool``) matches a registered built-in tool
is imported and re-registered, replacing the built-in handler and schema.

New files that don't match any built-in tool name are imported as additional
tools.

Configuration
-------------
The directory can be configured via ``config["tools"]["custom_tools_dir"]``
or the ``HERMES_CUSTOM_TOOLS_DIR`` environment variable.  Both default to
``~/.hermes/custom_tools/``.

Security
--------
Custom tools execute with the same permissions as built-in tools — they have
full access to the local system, API keys, and the internet.  Only the user
controls this directory; no remote code is ever downloaded or executed.

Usage
-----
Place ``*.py`` files in the custom tools directory.  Each file must call
``registry.register()`` at module level (same contract as built-in tools)::

    # ~/.hermes/custom_tools/browser_tool.py
    from tools import registry

    registry.register(
        name="browser_navigate",
        toolset="browser",
        schema={...},
        handler=my_navigate,
        check_fn=...,
        description="Navigate to a URL using headed Chrome CDP",
    )

On import, the custom module's ``register()`` calls replace the built-in
tools automatically.  No ``override=True`` flag needed — the loader patches
the registry to allow overwrites for custom tools.
"""

import importlib.util
import logging
import os
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def _get_custom_tools_dir() -> Optional[Path]:
    """Resolve the custom tools directory from config or env."""
    env_dir = os.environ.get("HERMES_CUSTOM_TOOLS_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser()

    try:
        from hermes_cli.config import load_config
        cfg = load_config()
        cfg_dir = cfg.get("custom_tools_dir") or ""
        if cfg_dir:
            return Path(cfg_dir).expanduser()
    except Exception:
        pass

    # Default: ~/.hermes/custom_tools/
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    return hermes_home / "custom_tools"


def _patch_registry_for_override():
    """Temporarily patch registry.register to set override=True.

    Custom tools call registry.register() directly.  We wrap it so that
    any registration originating from the custom tools directory automatically
    gets override=True, allowing it to replace built-in tools.
    """
    from tools import registry as reg_module

    original_register = reg_module.registry.register

    def _override_register(*args, **kwargs):
        kwargs.setdefault("override", True)
        return original_register(*args, **kwargs)

    reg_module.registry.register = _override_register
    return original_register


def _unpatch_registry(original_fn):
    """Restore the original registry.register function."""
    from tools import registry as reg_module
    reg_module.registry.register = original_fn


def _load_module_from_path(module_name: str, file_path: Path):
    """Import a Python file as a module without adding its parent to sys.path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        logger.error("Could not load spec for %s (%s)", module_name, file_path)
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _module_registers_tools(module_path: Path) -> bool:
    """Return True when the module contains a top-level registry.register() call."""
    import ast
    try:
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(module_path))
    except (OSError, SyntaxError):
        return False

    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if (isinstance(func, ast.Attribute)
                and func.attr == "register"
                and isinstance(func.value, ast.Name)
                and func.value.id == "registry"):
            return True
    return False


def discover_and_load_custom_tools(tools_dir: Optional[Path] = None) -> List[str]:
    """Scan the custom tools directory and load matching modules.

    For each ``*.py`` file that contains top-level ``registry.register()``
    calls, the module is imported with ``override=True`` auto-applied,
    allowing it to replace built-in tool implementations.

    Returns the list of successfully imported module names.
    """
    custom_dir = tools_dir or _get_custom_tools_dir()
    if custom_dir is None or not custom_dir.is_dir():
        logger.debug("Custom tools directory not found: %s", custom_dir)
        return []

    imported: List[str] = []
    original_register = _patch_registry_for_override()

    try:
        for py_file in sorted(custom_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue

            module_name = f"custom_tools.{py_file.stem}"

            try:
                if not _module_registers_tools(py_file):
                    logger.debug(
                        "Skipping %s — no top-level registry.register() calls",
                        py_file.name,
                    )
                    continue

                _load_module_from_path(module_name, py_file)
                imported.append(module_name)
                logger.info("Custom tools loaded from %s", py_file.name)

            except Exception as e:
                logger.error(
                    "Failed to load custom tool %s: %s", py_file.name, e,
                    exc_info=True,
                )
    finally:
        _unpatch_registry(original_register)

    return imported

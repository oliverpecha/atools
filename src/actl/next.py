"""decide_next — Stage 0A terminal/hold precedence + rule discovery."""
from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from actl.layout import Layout
from actl.seq import read_state


def decide_next(
    layout: Layout,
    tag: str,
    session_probe: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, str]:
    layout.sprint_dir(tag)
    if not layout.sprint_dir(tag).is_dir() or not layout.state_file(tag).is_file():
        raise FileNotFoundError(f"Sprint not found: {tag}")
    state = read_state(layout, tag)
    status = state.get("status")
    if status == "done":
        return {"action": "done", "command": "", "reason": "Sprint is done"}
    if status == "aborted":
        return {"action": "aborted", "command": "", "reason": "Sprint is aborted"}
    if status == "hold":
        return {
            "action": "hold_owner",
            "command": "",
            "reason": "Sprint is on hold for owner review",
        }

    rules_dir = Path(__file__).resolve().parent / "next_rules"
    modules: list[tuple[int, str, Any]] = []
    if rules_dir.is_dir():
        for p in rules_dir.glob("*.py"):
            if p.name.startswith("_"):
                continue
            mod_name = f"actl.next_rules.{p.stem}"
            # Always load from file to avoid stale sys.modules in tests
            spec = importlib.util.spec_from_file_location(mod_name, p)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            # Also register under bare stem for scratch tests
            sys.modules[p.stem] = mod
            spec.loader.exec_module(mod)
            pri = int(getattr(mod, "PRIORITY", 100))
            modules.append((pri, p.stem, mod))
    modules.sort(key=lambda t: (t[0], t[1]))
    for _pri, _stem, mod in modules:
        evaluate = getattr(mod, "evaluate", None)
        if not callable(evaluate):
            continue
        try:
            res = evaluate(layout, tag, session_probe=session_probe)
        except TypeError:
            res = evaluate(layout, tag)
        if res is not None:
            return {
                "action": str(res["action"]),
                "command": str(res["command"]),
                "reason": str(res["reason"]),
            }
    return {
        "action": "noop",
        "command": "",
        "reason": "No matching rule for current sprint state",
    }

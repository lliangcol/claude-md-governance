"""Shared hook configuration helpers."""
from __future__ import annotations

from typing import Any


def desired_hooks(config_mode: str) -> dict[str, Any]:
    normalized_mode = str(config_mode).lower()
    hooks: dict[str, Any] = {
        "PreToolUse": [
            {
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py pre"}],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py post"}],
            }
        ],
    }
    if normalized_mode != "off":
        hooks["ConfigChange"] = [
            {"matcher": "", "hooks": [{"type": "command", "command": "python scripts/claude_hook_guard.py config"}]}
        ]
    return {"hooks": hooks}


def merge_hook_settings(current: dict[str, Any], template: dict[str, Any]) -> bool:
    current.setdefault("hooks", {})
    changed = False
    for event, items in template.get("hooks", {}).items():
        current["hooks"].setdefault(event, [])
        existing = [repr(sorted(item.items())) for item in current["hooks"].get(event, []) if isinstance(item, dict)]
        for item in items:
            item_key = repr(sorted(item.items()))
            if item_key not in existing:
                current["hooks"][event].append(item)
                existing.append(item_key)
                changed = True
    return changed

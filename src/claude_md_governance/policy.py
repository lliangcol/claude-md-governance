"""Policy loading, defaulting, and migration helpers."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .policy_schema import (
    PolicyValidationError as PolicyValidationError,
    load_policy_file as load_policy_file,
    validate_policy as validate_policy,
)

ROOT_DOC_KEYS = ("root_doc", "root_agents", "root_claude")
DEFAULT_ROOT_DOC_PATH = "AGENTS.md"
LEGACY_ROOT_DOC_PATH = "CLAUDE.md"


def resolve_policy_path(repo: Path, policy: str | Path) -> Path:
    candidate = Path(policy)
    return candidate if candidate.is_absolute() else repo / candidate


def root_doc_policy(policy: dict[str, Any]) -> dict[str, Any]:
    for key in ROOT_DOC_KEYS:
        value = policy.get(key)
        if isinstance(value, dict):
            return value
    return {}


def root_doc_path(policy: dict[str, Any], default: str = LEGACY_ROOT_DOC_PATH) -> str:
    return str(root_doc_policy(policy).get("path", default))


def root_doc_rel(policy: dict[str, Any], default: str = LEGACY_ROOT_DOC_PATH) -> Path:
    return Path(root_doc_path(policy, default=default))


def root_doc_name(policy: dict[str, Any], default: str = LEGACY_ROOT_DOC_PATH) -> str:
    return root_doc_rel(policy, default=default).name


def policy_list_identity(item: Any) -> str:
    if isinstance(item, dict):
        for key in ("id", "name", "path"):
            value = item.get(key)
            if value:
                return f"{key}:{value}"
        return json.dumps(item, ensure_ascii=False, sort_keys=True)
    return str(item)


def merge_policy_defaults(existing: Any, defaults: Any) -> Any:
    if isinstance(existing, dict) and isinstance(defaults, dict):
        merged = dict(existing)
        for key, value in defaults.items():
            merged[key] = merge_policy_defaults(merged[key], value) if key in merged else value
        return merged
    if isinstance(existing, list) and isinstance(defaults, list):
        merged_list = list(existing)
        seen = {policy_list_identity(item) for item in merged_list}
        for item in defaults:
            identity = policy_list_identity(item)
            if identity not in seen:
                merged_list.append(item)
                seen.add(identity)
        return merged_list
    return existing


def normalize_policy_for_template_merge(existing: dict[str, Any]) -> dict[str, Any]:
    """Preserve legacy root-doc choices before applying new template defaults."""
    migrated = copy.deepcopy(existing)
    if "root_doc" in migrated:
        return migrated
    for key in ("root_agents", "root_claude"):
        value = migrated.get(key)
        if isinstance(value, dict):
            migrated["root_doc"] = copy.deepcopy(value)
            break
    return migrated


def migrate_policy(policy: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    migrated = copy.deepcopy(policy)
    actions: list[str] = []

    if "root_doc" not in migrated and isinstance(migrated.get("root_agents"), dict):
        migrated["root_doc"] = copy.deepcopy(migrated["root_agents"])
        actions.append("copied root_agents to root_doc")
    if "root_doc" not in migrated and isinstance(migrated.get("root_claude"), dict):
        migrated["root_doc"] = copy.deepcopy(migrated["root_claude"])
        actions.append("copied root_claude to root_doc")
    if "root_doc" not in migrated:
        migrated["root_doc"] = {"path": DEFAULT_ROOT_DOC_PATH}
        actions.append(f"added root_doc.path={DEFAULT_ROOT_DOC_PATH}")

    hooks = migrated.setdefault("hooks", {})
    if isinstance(hooks, dict) and "config_change_mode" not in hooks:
        hooks["config_change_mode"] = "block"
        actions.append("added hooks.config_change_mode=block")

    ci = migrated.setdefault("ci", {})
    if isinstance(ci, dict) and "provider" not in ci:
        ci["provider"] = "none"
        actions.append("added ci.provider=none")

    return migrated, actions

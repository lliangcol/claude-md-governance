"""Policy loading and validation helpers.

The runtime validator intentionally stays in the standard library. The JSON
Schema file shipped with the package is for editors, documentation, and external
validators; command behavior must not require a third-party schema package.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PolicyValidationError(ValueError):
    """Raised when policy JSON cannot be trusted."""

    def __init__(self, path: Path, errors: list[str]) -> None:
        self.path = path
        self.errors = tuple(errors)
        super().__init__(format_policy_errors(path, errors))


def format_policy_errors(path: Path, errors: list[str] | tuple[str, ...]) -> str:
    joined = "; ".join(errors) if errors else "unknown validation error"
    return f"Invalid policy file {path}: {joined}"


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_root_doc(errors: list[str], value: Any, key: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return
    path = value.get("path")
    if path is not None and not _is_non_empty_string(path):
        errors.append(f"{key}.path must be a non-empty string")
    for limit_key in ("warn_lines", "max_lines", "hard_fail_lines", "warn_tokens", "hard_fail_tokens"):
        limit = value.get(limit_key)
        if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 0):
            errors.append(f"{key}.{limit_key} must be a non-negative integer")


def _validate_required_sections(errors: list[str], value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append("required_sections must be an array")
        return
    for index, item in enumerate(value):
        item_path = f"required_sections[{index}]"
        if isinstance(item, str):
            if not item.strip():
                errors.append(f"{item_path} must not be empty")
            continue
        if not isinstance(item, dict):
            errors.append(f"{item_path} must be a string or object")
            continue
        if not _is_non_empty_string(item.get("name")):
            errors.append(f"{item_path}.name must be a non-empty string")
        aliases = item.get("aliases", [])
        if aliases is not None and (
            not isinstance(aliases, list) or any(not _is_non_empty_string(alias) for alias in aliases)
        ):
            errors.append(f"{item_path}.aliases must be an array of non-empty strings")
        severity = item.get("severity", "warning")
        if severity not in {"error", "warning"}:
            errors.append(f"{item_path}.severity must be error or warning")
        deduction = item.get("deduction", 4)
        if not isinstance(deduction, int) or isinstance(deduction, bool) or deduction < 0:
            errors.append(f"{item_path}.deduction must be a non-negative integer")


def _validate_string_list(errors: list[str], value: Any, key: str) -> None:
    if value is None:
        return
    if not isinstance(value, list) or any(not _is_non_empty_string(item) for item in value):
        errors.append(f"{key} must be an array of non-empty strings")


def _validate_sensitive_paths(errors: list[str], value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append("sensitive_paths must be an array")
        return
    for index, item in enumerate(value):
        item_path = f"sensitive_paths[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_path} must be an object")
            continue
        if not _is_non_empty_string(item.get("path")):
            errors.append(f"{item_path}.path must be a non-empty string")
        local_keys = ("local_doc", "local_agents", "local_claude")
        if any(key in item for key in local_keys) and not any(_is_non_empty_string(item.get(key)) for key in local_keys):
            errors.append(f"{item_path} must define a non-empty local_doc, local_agents, or local_claude")
        _validate_string_list(errors, item.get("required_tests", []), f"{item_path}.required_tests")
        _validate_string_list(errors, item.get("detect_keywords", []), f"{item_path}.detect_keywords")
        protected = item.get("protected", False)
        if not isinstance(protected, bool):
            errors.append(f"{item_path}.protected must be a boolean")


def _validate_hooks(errors: list[str], value: Any) -> None:
    if value is None:
        errors.append("hooks must be an object")
        return
    if not isinstance(value, dict):
        errors.append("hooks must be an object")
        return
    settings_path = value.get("settings_path")
    if settings_path is not None and not _is_non_empty_string(settings_path):
        errors.append("hooks.settings_path must be a non-empty string")
    if "config_change_mode" not in value:
        errors.append("hooks.config_change_mode is required")
    mode = value.get("config_change_mode", "block")
    if mode not in {"block", "warn", "off"}:
        errors.append("hooks.config_change_mode must be one of: block, warn, off")
    for key in ("require_pretool_guard", "require_posttool_quality_gate", "protected_config_review_required"):
        configured = value.get(key)
        if configured is not None and not isinstance(configured, bool):
            errors.append(f"hooks.{key} must be a boolean")


def validate_policy(policy: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(policy, dict):
        return ["policy root must be a JSON object"]

    version = policy.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        errors.append("version must be a positive integer")
    if not _is_non_empty_string(policy.get("preset")):
        errors.append("preset must be a non-empty string")

    threshold = policy.get("score_threshold", 75)
    if not isinstance(threshold, int) or isinstance(threshold, bool) or not 0 <= threshold <= 100:
        errors.append("score_threshold must be an integer between 0 and 100")

    _validate_root_doc(errors, policy.get("root_doc"), "root_doc")
    _validate_root_doc(errors, policy.get("root_agents"), "root_agents")
    _validate_root_doc(errors, policy.get("root_claude"), "root_claude")
    _validate_required_sections(errors, policy.get("required_sections", []))
    _validate_string_list(errors, policy.get("protected_paths", []), "protected_paths")
    _validate_sensitive_paths(errors, policy.get("sensitive_paths", []))
    _validate_hooks(errors, policy.get("hooks"))

    ci = policy.get("ci")
    if ci is not None:
        if not isinstance(ci, dict):
            errors.append("ci must be an object")
        else:
            provider = ci.get("provider")
            if provider is not None and provider not in {"auto", "github", "codeup", "none"}:
                errors.append("ci.provider must be one of: auto, github, codeup, none")

    behavior = policy.get("behavior_tests")
    if behavior is not None:
        if not isinstance(behavior, dict):
            errors.append("behavior_tests must be an object")
        else:
            enabled = behavior.get("enabled_by_default")
            if enabled is not None and not isinstance(enabled, bool):
                errors.append("behavior_tests.enabled_by_default must be a boolean")
            case_file = behavior.get("case_file")
            if case_file is not None and not _is_non_empty_string(case_file):
                errors.append("behavior_tests.case_file must be a non-empty string")

    return errors


def load_policy_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise PolicyValidationError(path, ["policy file is missing"])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PolicyValidationError(path, [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]) from exc
    errors = validate_policy(data)
    if errors:
        raise PolicyValidationError(path, errors)
    return data

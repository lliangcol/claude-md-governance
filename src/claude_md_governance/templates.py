"""Helpers for package-managed templates."""
from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
TEMPLATE_ROOT = PACKAGE_ROOT / "data" / "templates"


def template_root() -> Path:
    return TEMPLATE_ROOT


def policy_path(preset: str) -> Path:
    candidate = TEMPLATE_ROOT / "policies" / f"{preset}.json"
    if candidate.exists():
        return candidate
    return TEMPLATE_ROOT / "policies" / "generic.json"

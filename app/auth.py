"""Backward-compatible authentication imports."""

from app.core.auth import Principal, get_principal, require_role

__all__ = ["Principal", "get_principal", "require_role"]

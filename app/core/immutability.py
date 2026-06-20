from typing import Any, cast

from sqlalchemy import event as sqlalchemy_event
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models import AuditEvent, CalculationSnapshot, FactorVersion, ModelTemplateVersion

_registered = False


def register_immutability_guards() -> None:
    global _registered
    if _registered:
        return

    @sqlalchemy_event.listens_for(Session, "before_flush")
    def prevent_mutation_of_frozen_records(session: Session, *_args) -> None:
        for obj in session.dirty:
            if isinstance(obj, (CalculationSnapshot, AuditEvent)):
                if session.is_modified(obj, include_collections=True):
                    raise ValueError(f"{obj.__class__.__name__} is append-only")
            if isinstance(obj, (FactorVersion, ModelTemplateVersion)):
                state = cast(Any, inspect(obj))
                approved_history = state.attrs.approved.history
                was_approved = approved_history.deleted == [True] or (
                    not approved_history.has_changes() and obj.approved
                )
                if was_approved and session.is_modified(obj, include_collections=True):
                    raise ValueError(
                        f"Approved {obj.__class__.__name__} records are immutable"
                    )
        for obj in session.deleted:
            if isinstance(obj, (CalculationSnapshot, AuditEvent)):
                raise ValueError(f"{obj.__class__.__name__} is append-only")
            if isinstance(obj, (FactorVersion, ModelTemplateVersion)) and obj.approved:
                raise ValueError(
                    f"Approved {obj.__class__.__name__} records are immutable"
                )

    _registered = True

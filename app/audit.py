from sqlalchemy.orm import Session

from app.models import AuditEvent


def record_audit(
    db: Session,
    *,
    actor: str,
    action: str,
    object_type: str,
    object_id: str,
    before_hash: str | None = None,
    after_hash: str | None = None,
    details: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before_hash=before_hash,
        after_hash=after_hash,
        details=details or {},
    )
    db.add(event)
    return event


from datetime import datetime, timezone
import uuid
from app.db.schema import audit_events
from app.db.codec import json_dumps


def now():
    return datetime.now(timezone.utc).isoformat()


def audit(conn, action, subject, details=None):
    conn.execute(
        audit_events.insert().values(
            id=uuid.uuid4().hex,
            created_at=now(),
            action=action,
            subject=subject,
            details_json=json_dumps(details or {}),
        )
    )

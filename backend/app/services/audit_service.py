import hashlib
import json
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from typing import Any

class AuditService:
    @staticmethod
    def log_event(db: Session, request_id: str, event_type: str, event_data: Any, user_id: str = None) -> AuditLog:
        # Prevent concurrent modification issues by locking or getting the absolute latest
        # In SQLite, table locking handles this. In Postgres, we could use serializable isolation.
        last_record = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        prev_hash = last_record.record_hash if last_record else "GENESIS"

        event_data_str = json.dumps(event_data, sort_keys=True)
        user_id_str = str(user_id) if user_id else "NONE"
        
        # Tamper-evident chaining
        raw_data = f"{request_id}{user_id_str}{event_type}{event_data_str}{prev_hash}"
        new_hash = hashlib.sha256(raw_data.encode()).hexdigest()

        record = AuditLog(
            request_id=request_id,
            user_id=user_id,
            event_type=event_type,
            event_data=event_data_str,
            previous_hash=prev_hash,
            record_hash=new_hash
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

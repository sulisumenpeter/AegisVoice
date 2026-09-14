import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True) # Nullable for unauth attempts
    event_type = Column(String, nullable=False)
    event_data = Column(String, nullable=False) # JSON stringified
    previous_hash = Column(String, nullable=False)
    record_hash = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

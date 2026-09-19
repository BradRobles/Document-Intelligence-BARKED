import uuid
from sqlalchemy import Column, String, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.database import Base

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Job(Base):
    __tablename__ = "jobs"

    # Usamos UUID por seguridad para que no se puedan adivinar los IDs de otros usuarios
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String, index=True, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    extracted_text = Column(Text, nullable=True)
    metadata_info = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models import JobStatus

class JobResponse(BaseModel):
    id: UUID
    filename: str
    status: JobStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class JobDetailResponse(JobResponse):
    extracted_text: Optional[str] = None
    metadata_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    updated_at: datetime

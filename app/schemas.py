from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID
from app.models import JobStatus

class JobResponse(BaseModel):
    id: UUID
    filename: str
    status: JobStatus

    # Configuración Pydantic V2 equivalente a orm_mode=True
    model_config = ConfigDict(from_attributes=True)

class JobDetailResponse(JobResponse):
    extracted_text: Optional[str] = None
    metadata_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from celery import Celery
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models import Job, JobStatus

celery_app = Celery("document_pipeline")

celery_app.conf.update(
    broker_url=settings.REDIS_BROKER_URL,
    result_backend=settings.REDIS_BACKEND_URL,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    broker_transport_options={
        "visibility_timeout": 3600,
    },
    task_track_started=True,
    # Tolerancia a fallos de workers (redelivery)
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

def extract_text_from_pdf(file_path: str) -> tuple[str, dict]:
    doc = fitz.open(file_path)
    text = ""
    parser_used = "PyMuPDF (native)"
    
    for page in doc:
        text += page.get_text()
        
    # OCR Fallback para PDFs escaneados
    if not text.strip():
        parser_used = "PyTesseract (OCR Fallback)"
        text = ""
        for page in doc:
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text += pytesseract.image_to_string(img)
            
    metadata = {
        "page_count": doc.page_count,
        "format": doc.metadata.get("format", "PDF"),
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
        "parser_used": parser_used,
        "word_count": len(text.split())
    }
    doc.close()
    return text, metadata

def extract_text_from_image(file_path: str) -> tuple[str, dict]:
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image)
    metadata = {
        "width": image.width,
        "height": image.height,
        "format": image.format,
        "mode": image.mode,
        "parser_used": "PyTesseract",
        "word_count": len(text.split())
    }
    return text, metadata

def extract_text_from_txt(file_path: str) -> tuple[str, dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    metadata = {
        "size_bytes": os.path.getsize(file_path),
        "parser_used": "Python standard library",
        "word_count": len(text.split())
    }
    return text, metadata

@celery_app.task(bind=True, max_retries=3, acks_late=True)
def process_document(self, job_id: str, file_path: str, content_type: str):
    db: Session = SessionLocal()
    
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"status": "error", "message": f"Job {job_id} no encontrado en la base de datos"}

        job.status = JobStatus.PROCESSING
        db.commit()

        # Validación estricta de archivo físico vacío
        if os.path.getsize(file_path) == 0:
            raise ValueError("El archivo subido está vacío (0 bytes)")

        extracted_text = ""
        metadata = {}

        if content_type == "application/pdf":
            extracted_text, metadata = extract_text_from_pdf(file_path)
        elif content_type in ["image/png", "image/jpeg"]:
            extracted_text, metadata = extract_text_from_image(file_path)
        elif content_type == "text/plain":
            extracted_text, metadata = extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Formato no soportado por el motor de extracción: {content_type}")

        # Validación de texto vacío
        if not extracted_text.strip():
            raise ValueError("No se pudo extraer ningún texto legible del documento (archivo vacío o ruido)")

        # Enriquecer metadata
        metadata["attempts"] = self.request.retries + 1

        job.extracted_text = extracted_text.strip()
        job.metadata_info = metadata
        job.status = JobStatus.COMPLETED
        db.commit()

        return {"status": "success", "job_id": job_id}

    except Exception as exc:
        db.rollback()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = f"Error procesando documento: {str(exc)}"
            
            # Guardar el número de intento incluso en los fallos
            existing_meta = job.metadata_info or {}
            existing_meta["attempts"] = self.request.retries + 1
            job.metadata_info = existing_meta
            
            db.commit()
            
        return {"status": "failed", "error": str(exc)}
    
    finally:
        db.close()

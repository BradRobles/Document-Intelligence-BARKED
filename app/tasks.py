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
)

def extract_text_from_pdf(file_path: str) -> tuple[str, dict]:
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    
    metadata = {
        "page_count": doc.page_count,
        "format": doc.metadata.get("format", "PDF"),
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", "")
    }
    doc.close()
    return text, metadata

def extract_text_from_image(file_path: str) -> tuple[str, dict]:
    image = Image.open(file_path)
    # PyTesseract requiere que el binario de tesseract esté instalado en el sistema (lo cual hicimos en el Dockerfile)
    text = pytesseract.image_to_string(image)
    metadata = {
        "width": image.width,
        "height": image.height,
        "format": image.format,
        "mode": image.mode
    }
    return text, metadata

def extract_text_from_txt(file_path: str) -> tuple[str, dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    metadata = {
        "size_bytes": os.path.getsize(file_path)
    }
    return text, metadata

@celery_app.task(bind=True, max_retries=3)
def process_document(self, job_id: str, file_path: str, content_type: str):
    # Inicializar la sesión de base de datos
    db: Session = SessionLocal()
    
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"status": "error", "message": f"Job {job_id} no encontrado en la base de datos"}

        # 1. Marcar como procesando
        job.status = JobStatus.PROCESSING
        db.commit()

        extracted_text = ""
        metadata = {}

        # 2. Elegir el extractor según el tipo de archivo (Document Intelligence)
        if content_type == "application/pdf":
            extracted_text, metadata = extract_text_from_pdf(file_path)
        elif content_type in ["image/png", "image/jpeg"]:
            extracted_text, metadata = extract_text_from_image(file_path)
        elif content_type == "text/plain":
            extracted_text, metadata = extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Formato no soportado por el motor de extracción: {content_type}")

        # 3. Guardar resultados y marcar como completado
        job.extracted_text = extracted_text.strip()
        job.metadata_info = metadata
        job.status = JobStatus.COMPLETED
        db.commit()

        return {"status": "success", "job_id": job_id}

    except Exception as exc:
        db.rollback()
        # 4. Manejo de fallos: Actualizar a FAILED y guardar el error para que el usuario pueda consultarlo
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = f"Error procesando documento: {str(exc)}"
            db.commit()
        
        # En caso de fallos transitorios se podría usar: raise self.retry(exc=exc, countdown=10)
        return {"status": "failed", "error": str(exc)}
    
    finally:
        db.close()

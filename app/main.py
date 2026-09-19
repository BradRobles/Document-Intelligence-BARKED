import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import engine, Base, get_db
from app.models import Job, JobStatus
from app.schemas import JobResponse, JobDetailResponse
from app.tasks import process_document

# Crear tablas automáticamente al iniciar (en producción se usaría Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Document Intelligence API",
    description="Asynchronous pipeline para procesamiento de documentos",
    version="1.0.0"
)

UPLOAD_DIR = "/app/uploads"
# Asegurar que exista el directorio (en Docker debería existir por el volumen)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_FORMATS = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpg",
    "text/plain": "txt"
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit for reasonable processing time

@app.post("/upload", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Recibe un documento, lo almacena físicamente (Claim-Check) y 
    encola un trabajo asíncrono para su procesamiento.
    """
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo excede el límite razonable de 10 MB"
        )
        
    if file.content_type not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
            detail=f"Formato no soportado. Se permite: {list(ALLOWED_FORMATS.keys())}"
        )

    # Generar un ID único para el archivo y trabajo
    job_id = uuid.uuid4()
    
    # Nombre seguro en disco para evitar colisiones
    safe_filename = f"{job_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    # Implementación del Patrón Claim-Check: 
    # 1. Guardar el archivo pesado (Payload) en el almacenamiento.
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error guardando el archivo.")

    # 2. Guardar la referencia en la BD
    new_job = Job(
        id=job_id,
        filename=file.filename,
        file_path=file_path,
        status=JobStatus.PENDING
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # 3. Enviar a la cola de mensajes pasando solo la referencia (ID y Ruta)
    process_document.delay(str(new_job.id), file_path, file.content_type)

    return new_job

@app.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job_status(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Permite consultar el estado actual del procesamiento y recuperar el texto extraído
    y los metadatos una vez que el estado es COMPLETED.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trabajo no encontrado")
    
    return job

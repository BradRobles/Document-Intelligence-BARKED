# Document Intelligence Asynchronous Pipeline

Este proyecto implementa una arquitectura basada en el **Patrón Claim-Check** para procesar y extraer texto de documentos (PDF, TXT, PNG, JPG) de manera asíncrona. 

Es ideal para escenarios donde la extracción de texto (OCR) toma tiempo y no queremos mantener la conexión HTTP bloqueada con el usuario.

## Arquitectura y Tecnologías
- **API Web:** FastAPI (Python 3.11)
- **Cola Asíncrona (Queue):** Celery 5.3
- **Message Broker & Result Backend:** Redis 7 (usando bases de datos separadas `/0` y `/1`)
- **Base de Datos (Job Tracking):** PostgreSQL 15 + SQLAlchemy 2.0
- **Inteligencia de Documentos (OCR/Parser):** 
  - `PyMuPDF` (para documentos nativos PDF y TXT)
  - `PyTesseract` (para Imágenes escaneadas)
- **Monitoreo:** Celery Flower
- **Infraestructura:** Docker & Docker Compose

---

## 🚀 Guía de Despliegue en Otras Computadoras (Producción/Pruebas)

Todo el proyecto está diseñado para ser portátil (Portable) y "Dockerizado", de modo que no dependas de librerías locales instaladas en la computadora anfitriona.

### 1. Prerrequisitos
La computadora anfitriona **solo** necesita tener instalado:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Git (opcional, para clonar el repositorio)

### 2. Pasos de Instalación
1. **Clonar o copiar la carpeta del proyecto** en la nueva máquina.
   ```bash
   git clone <tu-repositorio> document_pipeline
   cd document_pipeline
   ```

2. **Levantar la Infraestructura**
   Ejecuta el siguiente comando. Docker se encargará de descargar las imágenes de Python, instalar el binario de Tesseract en el sistema operativo del contenedor, configurar Redis, Postgres y levantar la API.
   ```bash
   docker compose up --build -d
   ```
   *(El flag `-d` o detached mode hará que corra en segundo plano).*

3. **Verificar el Despliegue**
   Puedes asegurar que los 5 contenedores (`api`, `worker`, `db`, `redis`, `flower`) estén sanos con:
   ```bash
   docker compose ps
   ```

---

## 📖 Uso del API

Una vez que el sistema esté corriendo, puedes interactuar con los servicios locales o a través de la IP del servidor.

### 1. Interfaz Interactiva de FastAPI (Swagger UI)
Accede a: [http://localhost:8000/docs](http://localhost:8000/docs)

Desde aquí puedes probar los *endpoints* principales:
- `POST /upload`: Envía un documento. El sistema aplicará el **Patrón Claim-Check** guardando el archivo físicamente en el volumen `/app/uploads`, creando un registro `PENDING` en PostgreSQL y enviando la orden a la cola de Celery/Redis.
  - **Importante:** Revisa la respuesta (*Response Body*) y **copia el ID real** que devuelve el sistema (ej. `ec8ed813-8b0e-49d9-963c-713ad71c1ab2`). No uses el ID falso de ejemplo de Swagger.
- `GET /jobs/{job_id}`: Pega el ID copiado para consultar el estado. Cuando cambie a `COMPLETED`, podrás ver el texto extraído (`extracted_text`) y la información adicional (`metadata_info`).

### 2. Panel de Monitoreo (Celery Flower)
Accede a: [http://localhost:5555](http://localhost:5555)

Este panel te permitirá visualizar los "Workers" activos, el estado de las colas, gráficas de rendimiento y los fallos (si subes un PDF corrupto, por ejemplo).

---

## 🛠️ Comandos de Utilidad para Mantenimiento

**Ver logs en tiempo real (útil para ver cómo trabaja Celery):**
```bash
docker compose logs -f
```

**Apagar todo el sistema sin borrar la base de datos:**
```bash
docker compose down
```

**Apagar el sistema y borrar la base de datos (Reset total):**
```bash
docker compose down -v
```

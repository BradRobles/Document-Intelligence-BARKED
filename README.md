# Document Intelligence Asynchronous Pipeline

This project implements an architecture based on the **Claim-Check Pattern** to asynchronously process and extract text from documents (PDF, TXT, PNG, JPG).

It is ideal for scenarios where text extraction (OCR) is time-consuming and we do not want to keep the HTTP connection blocked for the user.

## Architecture and Technologies
- **Web API:** FastAPI (Python 3.11)
- **Asynchronous Queue:** Celery 5.3
- **Message Broker & Result Backend:** Redis 7 (using separate databases `/0` and `/1`)
- **Database (Job Tracking):** PostgreSQL 15 + SQLAlchemy 2.0
- **Document Intelligence (OCR/Parser):** 
  - `PyMuPDF` (for native PDF and TXT documents)
  - `PyTesseract` (for scanned Images)
- **Monitoring:** Celery Flower
- **Infrastructure:** Docker & Docker Compose

---

## 🚀 Deployment Guide (Production/Testing)

The entire project is designed to be portable and Dockerized, so you do not depend on local libraries installed on the host machine.

### 1. Prerequisites
The host machine **only** needs to have installed:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Git (optional, to clone the repository)

### 2. Installation Steps
1. **Clone or copy the project folder** to the new machine.
   ```bash
   git clone https://github.com/BradRobles/Document-Intelligence-BARKED.git document_pipeline
   cd document_pipeline
   ```

2. **Spin up the Infrastructure**
   Run the following command. Docker will take care of downloading the Python images, installing the Tesseract binary in the container's OS, configuring Redis, Postgres, and starting the API.
   ```bash
   docker compose up --build -d
   ```
   *(The `-d` flag or detached mode will run it in the background).*

3. **Verify the Deployment**
   You can ensure that all 5 containers (`api`, `worker`, `db`, `redis`, `flower`) are healthy with:
   ```bash
   docker compose ps
   ```

---

## 📖 API Usage

Once the system is running, you can interact with the local services or via the server's IP.

### 1. Interactive FastAPI Interface (Swagger UI)
Access: [http://localhost:8000/docs](http://localhost:8000/docs)

From here you can test the main *endpoints*:
- `POST /upload`: Upload a document. The system will apply the **Claim-Check Pattern** by physically saving the file in the `/app/uploads` volume, creating a `PENDING` record in PostgreSQL, and sending the task to the Celery/Redis queue.
  - **Important:** Check the *Response Body* and **copy the real ID** returned by the system (e.g. `ec8ed813-8b0e-49d9-963c-713ad71c1ab2`). Do not use the fake example ID provided by Swagger.
- `GET /jobs/{job_id}`: Paste the copied ID to check the status. When it changes to `COMPLETED`, you will be able to see the extracted text (`extracted_text`) and additional information (`metadata_info`).

### 2. Monitoring Dashboard (Celery Flower)
Access: [http://localhost:5555](http://localhost:5555)

This dashboard allows you to visualize active "Workers", queue status, performance graphs, and any failures (for example, if you upload a corrupted PDF) in real-time.

---

## 🛠️ Utility Commands for Maintenance

**View real-time logs (useful to see how Celery works):**
```bash
docker compose logs -f
```

**Shut down the entire system without deleting the database:**
```bash
docker compose down
```

**Shut down the system and delete the database (Total Reset):**
```bash
docker compose down -v
```

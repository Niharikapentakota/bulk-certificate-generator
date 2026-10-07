from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .schemas import (
    GenerationRequest, GenerationResponse,
    JobStatusResponse, RecipientResultResponse,
)
from .models import GenerationJob, Recipient
from .services.generator import generate_job_certificates

OUTPUT_DIR = Path("generated_certificates")
OUTPUT_DIR.mkdir(exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Bulk Certificate Generator API",
    version="1.0.0",
    description="Bulk certificate generation using FastAPI, SQLite and ReportLab.",
    lifespan=lifespan,
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs", response_model=GenerationResponse, status_code=202)
def create_job(
    payload: GenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = GenerationJob(status="pending", total=len(payload.recipients))
    db.add(job)
    db.flush()

    for item in payload.recipients:
        db.add(Recipient(
            job_id=job.id,
            name=item.name,
            email=str(item.email),
            course=item.course,
            completion_date=item.completion_date.isoformat(),
        ))

    db.commit()
    db.refresh(job)

    background_tasks.add_task(generate_job_certificates, job.id)
    return GenerationResponse(job_id=job.id, status=job.status, total=job.total)

@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = [
        RecipientResultResponse(
            id=r.id,
            name=r.name,
            email=r.email,
            status=r.status,
            certificate_url=f"/certificates/{r.id}" if r.status == "completed" else None,
            error_message=r.error_message,
        )
        for r in job.recipients
    ]

    processed = job.completed + job.failed
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        total=job.total,
        completed=job.completed,
        failed=job.failed,
        progress_percent=round((processed / job.total) * 100, 2) if job.total else 100,
        results=results,
    )

@app.get("/certificates/{recipient_id}")
def get_certificate(recipient_id: int, db: Session = Depends(get_db)):
    recipient = db.get(Recipient, recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if recipient.status != "completed" or not recipient.certificate_path:
        raise HTTPException(status_code=409, detail="Certificate is not available")

    path = Path(recipient.certificate_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Generated certificate file not found")

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
    )

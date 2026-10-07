from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import GenerationJob, Recipient

OUTPUT_DIR = Path("generated_certificates")
OUTPUT_DIR.mkdir(exist_ok=True)

def draw_certificate(path: Path, name: str, course: str, completion_date: str, certificate_id: str):
    """
    Single predefined certificate template.
    Keeping the layout in one function makes the template easy to change later.
    """
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(str(path), pagesize=(page_width, page_height))

    # Background/border
    c.setLineWidth(4)
    c.rect(30, 30, page_width - 60, page_height - 60)
    c.setLineWidth(1)
    c.rect(45, 45, page_width - 90, page_height - 90)

    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(page_width / 2, page_height - 105, "CERTIFICATE OF COMPLETION")

    c.setFont("Helvetica", 14)
    c.drawCentredString(page_width / 2, page_height - 145, "This certificate is proudly presented to")

    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(page_width / 2, page_height - 205, name)

    c.setFont("Helvetica", 15)
    c.drawCentredString(page_width / 2, page_height - 250, "for successfully completing")

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(page_width / 2, page_height - 285, course)

    c.setFont("Helvetica", 12)
    c.drawString(75, 85, f"Date: {completion_date}")
    c.drawRightString(page_width - 75, 85, f"Certificate ID: {certificate_id}")

    c.setFont("Helvetica", 11)
    c.drawCentredString(page_width / 2, 65, "Bulk Certificate Generator")
    c.save()

def generate_one(recipient_id: int):
    db = SessionLocal()
    try:
        recipient = db.get(Recipient, recipient_id)
        if not recipient:
            return

        recipient.status = "processing"
        db.commit()

        filename = f"certificate_{recipient.id}.pdf"
        path = OUTPUT_DIR / filename

        # Deliberate test hook: allows the test suite to prove one failure
        # does not stop the remaining recipients.
        if recipient.name.strip().upper() == "FAIL_TEST":
            raise RuntimeError("Simulated certificate generation failure")

        draw_certificate(
            path,
            recipient.name,
            recipient.course,
            recipient.completion_date,
            f"CERT-{recipient.id:06d}",
        )

        recipient.status = "completed"
        recipient.certificate_path = str(path)
        recipient.error_message = None
        db.commit()
    except Exception as exc:
        db.rollback()
        recipient = db.get(Recipient, recipient_id)
        if recipient:
            recipient.status = "failed"
            recipient.error_message = str(exc)[:1000]
            db.commit()
    finally:
        db.close()

def generate_job_certificates(job_id: int):
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if not job:
            return
        job.status = "processing"
        db.commit()
        recipient_ids = [r.id for r in job.recipients]
    finally:
        db.close()

    for recipient_id in recipient_ids:
        generate_one(recipient_id)

    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if not job:
            return
        recipients = list(job.recipients)
        job.completed = sum(r.status == "completed" for r in recipients)
        job.failed = sum(r.status == "failed" for r in recipients)
        job.status = "completed" if job.failed == 0 else (
            "failed" if job.completed == 0 else "partial"
        )
        db.commit()
    finally:
        db.close()

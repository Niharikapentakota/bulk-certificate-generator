# Bulk Certificate Generator

A backend API that accepts one bulk request containing multiple recipients, validates the data, generates PDF certificates from one predefined template, tracks progress, and serves completed certificates.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLite + SQLAlchemy
- ReportLab
- Pytest

## Why background processing?

The API returns `202 Accepted` and a `job_id` immediately instead of making the client wait for every PDF.

For this assignment, FastAPI `BackgroundTasks` is enough and keeps the architecture easy to understand. In a production system with very large jobs, this can be replaced with Celery/RQ + Redis without changing the API contract.

## Project Structure

```text
bulk_certificate_generator/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   └── services/
│       └── generator.py
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── generated_certificates/
├── requirements.txt
└── README.md
```

## Setup

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Create a bulk generation job

```http
POST /jobs
Content-Type: application/json
```

Example:

```json
{
  "recipients": [
    {
      "name": "Alice Johnson",
      "email": "alice@example.com",
      "course": "Python Backend Development",
      "completion_date": "2026-10-07"
    },
    {
      "name": "Bob Smith",
      "email": "bob@example.com",
      "course": "Python Backend Development",
      "completion_date": "2026-10-07"
    }
  ]
}
```

Response:

```json
{
  "job_id": 1,
  "status": "pending",
  "total": 2
}
```

The job is processed in the background.

## Check job status

```http
GET /jobs/1
```

Example completed response:

```json
{
  "job_id": 1,
  "status": "completed",
  "total": 2,
  "completed": 2,
  "failed": 0,
  "progress_percent": 100.0,
  "results": [
    {
      "id": 1,
      "name": "Alice Johnson",
      "email": "alice@example.com",
      "status": "completed",
      "certificate_url": "/certificates/1",
      "error_message": null
    }
  ]
}
```

Possible job states:

- `pending`
- `processing`
- `completed`
- `partial`
- `failed`

`partial` means at least one certificate succeeded and at least one failed.

## Retrieve a certificate

```http
GET /certificates/{recipient_id}
```

Example:

```text
GET /certificates/1
```

The API returns the generated PDF.

## Validation

Each recipient must contain:

- `name`: 2–150 characters
- `email`: valid email address
- `course`: 2–200 characters
- `completion_date`: valid ISO date

A request may contain up to 1000 recipients.

## Failure isolation

Each recipient is processed independently.

If one certificate fails:

1. That recipient is marked `failed`.
2. The exception is stored in `error_message`.
3. Other recipients continue processing.
4. The final job becomes `partial` if some succeeded.

The test suite uses the special name `FAIL_TEST` to simulate a generation failure.

## Testing

Run:

```bash
pytest -q
```

The tests cover:

- job creation
- input validation
- certificate generation
- job status/progress
- individual certificate failure
- certificate retrieval

## Design decisions

### 1. FastAPI

FastAPI provides validation through Pydantic and automatic OpenAPI/Swagger documentation.

### 2. SQLite

SQLite satisfies the relational database requirement and makes the assignment easy to run locally. PostgreSQL can be substituted later.

### 3. ReportLab

ReportLab generates actual PDF certificates without requiring an external office application.

### 4. One predefined template

The certificate layout is centralized in `draw_certificate()` in `app/services/generator.py`. There is intentionally no template editor or multi-template system because the requirement asks for one predefined template.

### 5. Background processing

The client does not wait for all certificates. It receives a job ID and polls the status endpoint.

### 6. Per-recipient status

The database stores the state of every recipient independently, which allows the API to report exactly which certificates succeeded or failed.

## Interview explanation in one minute

"The API accepts a list of recipients in a single POST request. I create a generation job and recipient records in SQLite, return a job ID with HTTP 202, and process each recipient in a FastAPI background task. ReportLab generates the PDF using one predefined template. Each recipient has its own status and error message, so a failure is isolated instead of aborting the complete batch. The client polls the job endpoint to see completed and failed counts, and completed certificates are available through a dedicated download endpoint. For production-scale workloads, I would replace FastAPI BackgroundTasks with a durable queue such as Celery or RQ with Redis."

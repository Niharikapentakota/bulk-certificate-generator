from datetime import date
from pydantic import BaseModel, EmailStr, Field, field_validator

class RecipientInput(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    course: str = Field(min_length=2, max_length=200)
    completion_date: date

    @field_validator("name", "course")
    @classmethod
    def strip_text(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value

class GenerationRequest(BaseModel):
    recipients: list[RecipientInput] = Field(min_length=1, max_length=1000)

class GenerationResponse(BaseModel):
    job_id: int
    status: str
    total: int

class RecipientResultResponse(BaseModel):
    id: int
    name: str
    email: str
    status: str
    certificate_url: str | None = None
    error_message: str | None = None

class JobStatusResponse(BaseModel):
    job_id: int
    status: str
    total: int
    completed: int
    failed: int
    progress_percent: float
    results: list[RecipientResultResponse]

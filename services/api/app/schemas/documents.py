from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

ALLOWED_MIME_TYPES = {"application/pdf", "text/plain", "text/markdown"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

TEXT_INGESTIBLE_MIME_TYPES = {"text/plain", "text/markdown"}
MAX_INGEST_CONTENT_CHARS = 2_000_000
CHUNK_WORDS = 750

Classification = Literal["public", "internal", "confidential", "restricted"]


class DocumentSummary(BaseModel):
    id: UUID
    title: str
    status: str
    classification: str
    created_at: datetime
    updated_at: datetime


class DocumentAccessResponse(BaseModel):
    document_id: UUID
    allowed: bool
    reason: str


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    department_id: UUID | None = None
    classification: Classification
    original_filename: str = Field(min_length=1)
    mime_type: str
    file_size_bytes: int = Field(gt=0)

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, value: str) -> str:
        if value not in ALLOWED_MIME_TYPES:
            raise ValueError(f"mime_type must be one of {sorted(ALLOWED_MIME_TYPES)}")
        return value

    @field_validator("file_size_bytes")
    @classmethod
    def validate_file_size(cls, value: int) -> int:
        if value > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"file_size_bytes must not exceed {MAX_FILE_SIZE_BYTES}")
        return value


class DocumentCreateResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    status: str
    classification: str
    created_at: datetime
    updated_at: datetime
    version_id: UUID
    version_number: int
    version_status: str


class IngestTextRequest(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_INGEST_CONTENT_CHARS)


class IngestTextResponse(BaseModel):
    document_id: UUID
    version_id: UUID
    version_status: str
    chunk_count: int

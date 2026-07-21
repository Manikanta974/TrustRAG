from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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

from uuid import UUID

from pydantic import BaseModel, Field


class RetrievalSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class RetrievalChunkResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    page_start: int | None
    page_end: int | None
    snippet: str
    score: float


class RetrievalSearchResponse(BaseModel):
    results: list[RetrievalChunkResult]

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.documents import (
    DocumentAccessResponse,
    DocumentCreateRequest,
    DocumentCreateResponse,
    DocumentSummary,
    IngestTextRequest,
    IngestTextResponse,
)
from app.schemas.membership import CurrentMembership
from app.services.auth import get_current_membership
from app.services.documents import (
    DocumentAccessDeniedError,
    DocumentIngestConflictError,
    DocumentNotFoundError,
    InvalidIngestContentError,
    PromptInjectionDetectedError,
    SensitiveDataBlockedError,
    check_document_access,
    create_document,
    ingest_text,
    list_accessible_documents,
)

router = APIRouter()


@router.get("/documents", response_model=list[DocumentSummary], tags=["documents"])
def list_documents(
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[DocumentSummary]:
    return list_accessible_documents(db, membership)


@router.post(
    "/documents",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
def create_document_endpoint(
    payload: DocumentCreateRequest,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> DocumentCreateResponse:
    try:
        return create_document(db, membership, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/documents/{document_id}/access",
    response_model=DocumentAccessResponse,
    tags=["documents"],
)
def get_document_access(
    document_id: UUID,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> DocumentAccessResponse:
    decision = check_document_access(db, membership, document_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="document not found")
    return decision


@router.post(
    "/documents/{document_id}/ingest-text",
    response_model=IngestTextResponse,
    tags=["documents"],
)
def ingest_text_endpoint(
    document_id: UUID,
    payload: IngestTextRequest,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> IngestTextResponse:
    try:
        return ingest_text(db, membership, document_id, payload.content)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="document not found") from exc
    except DocumentAccessDeniedError as exc:
        raise HTTPException(
            status_code=403, detail="not authorized to manage this document"
        ) from exc
    except DocumentIngestConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    except InvalidIngestContentError as exc:
        raise HTTPException(status_code=422, detail="content must not be empty") from exc
    except PromptInjectionDetectedError as exc:
        raise HTTPException(
            status_code=422, detail="content blocked: possible prompt injection"
        ) from exc
    except SensitiveDataBlockedError as exc:
        raise HTTPException(
            status_code=422, detail="content blocked: high-confidence secret detected"
        ) from exc

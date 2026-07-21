from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.documents import DocumentAccessResponse, DocumentSummary
from app.schemas.membership import CurrentMembership
from app.services.auth import get_current_membership
from app.services.documents import check_document_access, list_accessible_documents

router = APIRouter()


@router.get("/documents", response_model=list[DocumentSummary], tags=["documents"])
def list_documents(
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[DocumentSummary]:
    return list_accessible_documents(db, membership)


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

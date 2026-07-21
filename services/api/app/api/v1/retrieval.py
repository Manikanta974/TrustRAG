from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.membership import CurrentMembership
from app.schemas.retrieval import RetrievalSearchRequest, RetrievalSearchResponse
from app.services.auth import get_current_membership
from app.services.retrieval import search_chunks

router = APIRouter()


@router.post("/retrieval/search", response_model=RetrievalSearchResponse, tags=["retrieval"])
def retrieval_search(
    payload: RetrievalSearchRequest,
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> RetrievalSearchResponse:
    results = search_chunks(db, membership, payload.query, payload.limit)
    return RetrievalSearchResponse(results=results)

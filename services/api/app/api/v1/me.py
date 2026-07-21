from fastapi import APIRouter, Depends

from app.schemas.membership import CurrentMembership
from app.services.auth import get_current_membership

router = APIRouter()


@router.get("/me", response_model=CurrentMembership, tags=["identity"])
def read_current_membership(
    membership: CurrentMembership = Depends(get_current_membership),
) -> CurrentMembership:
    return membership

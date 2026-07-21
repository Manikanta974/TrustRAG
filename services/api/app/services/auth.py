from fastapi import Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.membership import CurrentMembership


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="authentication required")


def get_current_membership(
    x_dev_user_email: str | None = Header(default=None),
    x_dev_organization_slug: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> CurrentMembership:
    """Resolve the caller's organization membership from temporary dev headers.

    Stand-in for verified Supabase JWT identity (docs/SECURITY_MODEL.md) until
    that phase is implemented. Fails closed: any missing header, unknown
    organization/profile, or inactive/absent membership returns 401 rather
    than defaulting to access.
    """
    if not x_dev_user_email or not x_dev_organization_slug:
        raise _unauthorized()

    organization = db.execute(
        text(
            "select id, slug from organizations "
            "where lower(slug) = lower(:slug) and status = 'active'"
        ),
        {"slug": x_dev_organization_slug},
    ).mappings().first()
    if organization is None:
        raise _unauthorized()

    profile = db.execute(
        text(
            "select id, email from profiles "
            "where organization_id = :organization_id and lower(email) = lower(:email) "
            "and status = 'active'"
        ),
        {"organization_id": organization["id"], "email": x_dev_user_email},
    ).mappings().first()
    if profile is None:
        raise _unauthorized()

    membership = db.execute(
        text(
            "select m.role_id, r.name as role_name "
            "from organization_memberships m "
            "join organization_roles r on r.id = m.role_id "
            "where m.organization_id = :organization_id and m.profile_id = :profile_id "
            "and m.status = 'active' "
            "limit 1"
        ),
        {"organization_id": organization["id"], "profile_id": profile["id"]},
    ).mappings().first()
    if membership is None:
        raise _unauthorized()

    department = db.execute(
        text(
            "select d.id as department_id, d.name as department_name "
            "from department_memberships dm "
            "join departments d on d.id = dm.department_id "
            "where dm.organization_id = :organization_id and dm.profile_id = :profile_id "
            "and dm.status = 'active' "
            "limit 1"
        ),
        {"organization_id": organization["id"], "profile_id": profile["id"]},
    ).mappings().first()

    return CurrentMembership(
        profile_id=profile["id"],
        email=profile["email"],
        organization_id=organization["id"],
        organization_slug=organization["slug"],
        role_id=membership["role_id"],
        role_name=membership["role_name"],
        department_id=department["department_id"] if department else None,
        department_name=department["department_name"] if department else None,
    )

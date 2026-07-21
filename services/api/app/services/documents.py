from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.documents import DocumentAccessResponse, DocumentSummary
from app.schemas.membership import CurrentMembership

# Note: document_acl.principal_type has no 'organization' value in the migration
# (docs/DATA_MODEL.md / supabase/migrations/20260718000000_core_schema.sql); only
# user, department, group, and role grants exist, so no organization-wide ACL path
# is implemented here.
#
# Deliberately no blanket "admin sees every document" bypass: SECURITY_MODEL.md's
# effective-access decision is default-deny and only lists owner, explicit user,
# department, and role grants as valid paths. Admin gets broader access only
# because the seed grants the 'admin' role explicit document_acl rows (and owns
# some documents) — the same mechanism as any other principal, not a special case.

_READY_VERSION_EXISTS = (
    "exists (select 1 from document_versions dv "
    "where dv.document_id = d.id and dv.status = 'ready')"
)

_ACCESS_GRANT_EXISTS = (
    "("
    "d.owner_profile_id = :profile_id "
    "or exists (select 1 from document_acl a where a.document_id = d.id "
    "and a.principal_type = 'user' and a.principal_id = :profile_id) "
    "or exists (select 1 from document_acl a "
    "join department_memberships dm on dm.department_id = a.principal_id "
    "where a.document_id = d.id and a.principal_type = 'department' "
    "and dm.profile_id = :profile_id and dm.status = 'active') "
    "or exists (select 1 from document_acl a "
    "join group_members gm on gm.group_id = a.principal_id "
    "where a.document_id = d.id and a.principal_type = 'group' "
    "and gm.profile_id = :profile_id) "
    "or exists (select 1 from document_acl a where a.document_id = d.id "
    "and a.principal_type = 'role' and a.principal_id = :role_id)"
    ")"
)


def list_accessible_documents(db: Session, membership: CurrentMembership) -> list[DocumentSummary]:
    rows = (
        db.execute(
            text(
                "select d.id, d.title, d.status, d.classification, d.created_at, d.updated_at "
                "from documents d "
                "where d.organization_id = :organization_id "
                "and d.status = 'active' "
                f"and {_READY_VERSION_EXISTS} "
                f"and {_ACCESS_GRANT_EXISTS} "
                "order by d.created_at"
            ),
            {
                "organization_id": membership.organization_id,
                "profile_id": membership.profile_id,
                "role_id": membership.role_id,
            },
        )
        .mappings()
        .all()
    )
    return [DocumentSummary(**row) for row in rows]


def check_document_access(
    db: Session, membership: CurrentMembership, document_id: UUID
) -> DocumentAccessResponse | None:
    """Return the access decision for one document, or None if it does not
    exist or belongs to a different organization (caller must return 404 to
    avoid revealing cross-tenant document existence, per docs/API_CONTRACT.md).
    """
    document = (
        db.execute(
            text(
                "select id, organization_id, owner_profile_id, status "
                "from documents where id = :document_id"
            ),
            {"document_id": document_id},
        )
        .mappings()
        .first()
    )
    if document is None or document["organization_id"] != membership.organization_id:
        return None

    if document["status"] != "active":
        return DocumentAccessResponse(
            document_id=document_id, allowed=False, reason="document_not_active"
        )

    has_ready_version = db.execute(
        text(
            "select exists (select 1 from document_versions "
            "where document_id = :document_id and status = 'ready')"
        ),
        {"document_id": document_id},
    ).scalar()
    if not has_ready_version:
        return DocumentAccessResponse(
            document_id=document_id, allowed=False, reason="no_ready_version"
        )

    if document["owner_profile_id"] == membership.profile_id:
        return DocumentAccessResponse(document_id=document_id, allowed=True, reason="owner")

    grant = (
        db.execute(
            text(
                "select principal_type from document_acl a "
                "where a.document_id = :document_id and ("
                "(a.principal_type = 'user' and a.principal_id = :profile_id) "
                "or (a.principal_type = 'department' and exists ("
                "  select 1 from department_memberships dm "
                "  where dm.department_id = a.principal_id and dm.profile_id = :profile_id "
                "  and dm.status = 'active')) "
                "or (a.principal_type = 'group' and exists ("
                "  select 1 from group_members gm "
                "  where gm.group_id = a.principal_id and gm.profile_id = :profile_id)) "
                "or (a.principal_type = 'role' and a.principal_id = :role_id)"
                ") limit 1"
            ),
            {
                "document_id": document_id,
                "profile_id": membership.profile_id,
                "role_id": membership.role_id,
            },
        )
        .mappings()
        .first()
    )
    if grant is None:
        return DocumentAccessResponse(document_id=document_id, allowed=False, reason="no_grant")

    reason_by_principal_type = {
        "user": "explicit_user_grant",
        "department": "department_grant",
        "group": "group_grant",
        "role": "role_grant",
    }
    return DocumentAccessResponse(
        document_id=document_id,
        allowed=True,
        reason=reason_by_principal_type[grant["principal_type"]],
    )

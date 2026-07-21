from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.documents import (
    DocumentAccessResponse,
    DocumentCreateRequest,
    DocumentCreateResponse,
    DocumentSummary,
)
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


def create_document(
    db: Session, membership: CurrentMembership, payload: DocumentCreateRequest
) -> DocumentCreateResponse:
    """Create document + version metadata only (no file bytes, no storage,
    no scanning/parsing). Raises ValueError on an invalid department_id,
    which the caller must translate to 422.
    """
    if payload.department_id is not None:
        department_exists = db.execute(
            text(
                "select exists (select 1 from departments "
                "where id = :department_id and organization_id = :organization_id)"
            ),
            {
                "department_id": payload.department_id,
                "organization_id": membership.organization_id,
            },
        ).scalar()
        if not department_exists:
            raise ValueError("department_id does not belong to the caller's organization")

    document = (
        db.execute(
            text(
                "insert into documents "
                "(organization_id, owner_profile_id, title, description, status, classification) "
                "values (:organization_id, :owner_profile_id, :title, :description, "
                "'active', :classification) "
                "returning id, title, description, status, classification, created_at, updated_at"
            ),
            {
                "organization_id": membership.organization_id,
                "owner_profile_id": membership.profile_id,
                "title": payload.title,
                "description": payload.description,
                "classification": payload.classification,
            },
        )
        .mappings()
        .first()
    )

    storage_key = (
        f"{membership.organization_id}/documents/{document['id']}/v1/{payload.original_filename}"
    )
    # Version status is 'pending', not 'processing' or 'ready': no malware scan,
    # parsing, or PII/injection detection has run yet (those are later ingestion
    # phases). 'ready' would violate SECURITY_MODEL.md's "unsafe documents cannot
    # silently become LLM context"; 'processing' would falsely claim a pipeline
    # step already started. 'pending' matches the actual, documented first stage
    # of the document_versions lifecycle (docs/DATA_MODEL.md).
    version = (
        db.execute(
            text(
                "insert into document_versions "
                "(organization_id, document_id, version_number, storage_key, "
                "original_filename, mime_type, file_size_bytes, status) "
                "values (:organization_id, :document_id, 1, :storage_key, "
                ":original_filename, :mime_type, :file_size_bytes, 'pending') "
                "returning id, version_number, status"
            ),
            {
                "organization_id": membership.organization_id,
                "document_id": document["id"],
                "storage_key": storage_key,
                "original_filename": payload.original_filename,
                "mime_type": payload.mime_type,
                "file_size_bytes": payload.file_size_bytes,
            },
        )
        .mappings()
        .first()
    )

    if payload.department_id is not None:
        db.execute(
            text(
                "insert into document_acl "
                "(organization_id, document_id, principal_type, principal_id, permission) "
                "values (:organization_id, :document_id, 'department', :department_id, 'read')"
            ),
            {
                "organization_id": membership.organization_id,
                "document_id": document["id"],
                "department_id": payload.department_id,
            },
        )

    db.commit()

    return DocumentCreateResponse(
        id=document["id"],
        title=document["title"],
        description=document["description"],
        status=document["status"],
        classification=document["classification"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
        version_id=version["id"],
        version_number=version["version_number"],
        version_status=version["status"],
    )

import re
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.schemas.documents import (
    CHUNK_WORDS,
    TEXT_INGESTIBLE_MIME_TYPES,
    DocumentAccessResponse,
    DocumentCreateRequest,
    DocumentCreateResponse,
    DocumentSummary,
    IngestTextResponse,
)
from app.schemas.membership import CurrentMembership


class DocumentNotFoundError(Exception):
    """Document does not exist or belongs to a different organization."""


class DocumentAccessDeniedError(Exception):
    """Caller has no owner/user/department/group/role grant on the document."""


class DocumentIngestConflictError(Exception):
    """Document/version is not in a state eligible for text ingestion."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class InvalidIngestContentError(Exception):
    """Content is empty after normalization."""

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


def _normalize_text(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n").strip()


def _chunk_text(content: str, words_per_chunk: int = CHUNK_WORDS) -> list[tuple[str, int, int]]:
    """Split content into ~words_per_chunk-word chunks, preserving original
    formatting within each chunk and tracking char offsets for provenance.
    """
    words = list(re.finditer(r"\S+", content))
    chunks: list[tuple[str, int, int]] = []
    for i in range(0, len(words), words_per_chunk):
        batch = words[i : i + words_per_chunk]
        start_offset = batch[0].start()
        end_offset = batch[-1].end()
        chunks.append((content[start_offset:end_offset], start_offset, end_offset))
    return chunks


def _has_management_grant(db: Session, membership: CurrentMembership, document: dict) -> bool:
    """Owner/user/department/group/role grant check, deliberately without the
    ready-version gate used by check_document_access: managing a pending
    version (e.g. ingesting text into it) must be possible before it is ready.
    """
    if document["owner_profile_id"] == membership.profile_id:
        return True
    grant = (
        db.execute(
            text(
                "select 1 from document_acl a "
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
                "document_id": document["id"],
                "profile_id": membership.profile_id,
                "role_id": membership.role_id,
            },
        )
        .mappings()
        .first()
    )
    return grant is not None


def ingest_text(
    db: Session, membership: CurrentMembership, document_id: UUID, content: str
) -> IngestTextResponse:
    """Chunk TXT/Markdown content into document_chunks and mark the version
    ready. No embeddings are generated here (later ingestion phase).
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
        raise DocumentNotFoundError()

    if not _has_management_grant(db, membership, document):
        raise DocumentAccessDeniedError()

    if document["status"] != "active":
        raise DocumentIngestConflictError("document_not_active")

    version = (
        db.execute(
            text(
                "select id, status, mime_type from document_versions "
                "where document_id = :document_id "
                "order by version_number desc limit 1"
            ),
            {"document_id": document_id},
        )
        .mappings()
        .first()
    )
    if version is None:
        raise DocumentIngestConflictError("no_version")
    if version["status"] != "pending":
        raise DocumentIngestConflictError("version_not_pending")
    if version["mime_type"] not in TEXT_INGESTIBLE_MIME_TYPES:
        raise DocumentIngestConflictError("unsupported_mime_type")

    normalized = _normalize_text(content)
    if not normalized:
        raise InvalidIngestContentError()

    chunks = _chunk_text(normalized)

    for chunk_content, start_offset, end_offset in chunks:
        db.execute(
            text(
                "insert into document_chunks "
                "(organization_id, document_version_id, content, page_number, "
                "start_offset, end_offset) "
                "values (:organization_id, :version_id, :content, 1, :start_offset, :end_offset)"
            ),
            {
                "organization_id": membership.organization_id,
                "version_id": version["id"],
                "content": chunk_content,
                "start_offset": start_offset,
                "end_offset": end_offset,
            },
        )

    db.execute(
        text(
            "update document_versions set status = 'ready', updated_at = now() "
            "where id = :version_id"
        ),
        {"version_id": version["id"]},
    )
    # documents.status has no 'ready' value (only active/archived/deleted); it
    # already stays 'active', and readiness is solely tracked on the version
    # (docs/DATA_MODEL.md), so no document-row change is needed here.

    db.execute(
        text(
            "insert into audit_events "
            "(organization_id, actor_profile_id, action, resource_type, resource_id, "
            "decision, policy_version, metadata) "
            "values (:organization_id, :actor_profile_id, 'document_version.ingest_text', "
            "'document_version', :version_id, 'allow', 'v1', :metadata)"
        ).bindparams(bindparam("metadata", type_=JSONB)),
        {
            "organization_id": membership.organization_id,
            "actor_profile_id": membership.profile_id,
            "version_id": version["id"],
            "metadata": {"document_id": str(document_id), "chunk_count": len(chunks)},
        },
    )

    db.commit()

    return IngestTextResponse(
        document_id=document_id,
        version_id=version["id"],
        version_status="ready",
        chunk_count=len(chunks),
    )

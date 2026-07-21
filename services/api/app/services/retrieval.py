import hashlib

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.schemas.membership import CurrentMembership
from app.schemas.retrieval import RetrievalChunkResult
from app.services.documents import _ACCESS_GRANT_EXISTS

# Reuses the exact same owner/user/department/group/role grant predicate as
# document reads (app.services.documents) so retrieval can never authorize a
# chunk that GET /v1/documents would not. Score is a constant placeholder:
# this is plain ILIKE keyword search, not ranked vector retrieval.
SNIPPET_LENGTH = 300
PLACEHOLDER_SCORE = 1.0


def _build_snippet(content: str) -> str:
    if len(content) <= SNIPPET_LENGTH:
        return content
    return content[:SNIPPET_LENGTH].rstrip() + "…"


def search_chunks(
    db: Session, membership: CurrentMembership, query: str, limit: int
) -> list[RetrievalChunkResult]:
    rows = (
        db.execute(
            text(
                "select c.id as chunk_id, d.id as document_id, d.title as document_title, "
                "c.page_number, c.content "
                "from document_chunks c "
                "join document_versions v on v.id = c.document_version_id "
                "join documents d on d.id = v.document_id "
                "where d.organization_id = :organization_id "
                "and d.status = 'active' "
                "and v.status = 'ready' "
                "and c.content ilike :pattern "
                f"and {_ACCESS_GRANT_EXISTS} "
                "order by c.created_at "
                "limit :limit"
            ),
            {
                "organization_id": membership.organization_id,
                "profile_id": membership.profile_id,
                "role_id": membership.role_id,
                "pattern": f"%{query}%",
                "limit": limit,
            },
        )
        .mappings()
        .all()
    )

    results = [
        RetrievalChunkResult(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            document_title=row["document_title"],
            page_start=row["page_number"],
            page_end=row["page_number"],
            snippet=_build_snippet(row["content"]),
            score=PLACEHOLDER_SCORE,
        )
        for row in rows
    ]

    _record_query_run(db, membership, query=query, matched=bool(results), limit=limit)
    db.commit()

    return results


def _record_query_run(
    db: Session, membership: CurrentMembership, *, query: str, matched: bool, limit: int
) -> None:
    """Minimal query_runs record. question_hash only — raw query text is
    never stored, per docs/SECURITY_MODEL.md ("hash or redact question text
    by default").
    """
    question_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
    outcome = "answered" if matched else "insufficient_evidence"
    db.execute(
        text(
            "insert into query_runs "
            "(organization_id, profile_id, question_hash, outcome, model_config) "
            "values (:organization_id, :profile_id, :question_hash, :outcome, :model_config)"
        ).bindparams(bindparam("model_config", type_=JSONB)),
        {
            "organization_id": membership.organization_id,
            "profile_id": membership.profile_id,
            "question_hash": question_hash,
            "outcome": outcome,
            "model_config": {"endpoint": "retrieval_search", "limit": limit},
        },
    )

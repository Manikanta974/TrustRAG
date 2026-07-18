# TrustRAG security model

## Security invariants

1. Identity and tenant context originate from a verified Supabase JWT and server-side lookups.
2. Every query, chunk, storage object, policy, audit event, and document version is tenant-scoped.
3. Access is default-deny and requires a current, explicit effective policy grant.
4. A chunk is authorized before it enters any prompt, reranker, response, cache, trace, or application log.
5. Citation access causes a fresh access check.
6. Raw originals remain private; object keys and signed URLs are generated only after authorization.
7. Unsafe documents and queries cannot silently become LLM context.
8. Security-relevant decisions produce an audit event.

## Effective access decision

For a requested document, require: same tenant; active user; document version is `ready`; and one of document owner (where configured), explicit user grant, matching department grant, or a role grant. A future classification/clearance requirement is additive. Deny if any required policy source is unavailable or inconsistent.

The database query must use tenant and readiness predicates plus a policy-aware filter for efficiency. The FastAPI service must independently revalidate each candidate from current policy records, because index metadata can be stale or malformed.

## Prompt injection

Treat all document and user text as untrusted. Detect high-risk patterns such as instruction hierarchy manipulation, requests to reveal hidden prompts/secrets, tool-call directives, encoded payloads, and attempts to override access controls. Use deterministic rules plus an optional classifier; retain detector version and reason codes.

- **User query:** block clear bypass/exfiltration attempts; allow benign questions with a warning/telemetry path where appropriate.
- **Uploaded document:** scan before indexing; quarantine high-severity material for administrator review. Low-risk findings can be indexed only with explicit policy and visible flags.
- **Generation:** system instructions state that retrieved content is data, not instructions; no tools are exposed to document content; structured output and citation validation constrain results.

Detection reduces risk but is not an authorization control. Authorization is always enforced separately.

## PII and secret handling

Run detectors on extracted text before storage in searchable form. Recognize organization-defined PII categories and high-confidence credentials (API keys, private keys, passwords, tokens, connection strings). Store only minimal findings metadata in audit/security events; never copy detected secret values into logs.

Redaction mode is policy-driven:

- `mask`: replace sensitive spans before embedding and generation while preserving offsets/provenance.
- `quarantine`: prevent indexing until reviewed.
- `allow_restricted`: only for approved data classes with additional access policy and documented legal basis.

Redaction must occur consistently in chunks, embeddings, previews, exports, and prompts. Original encrypted documents require separate authorization and are not silently modified.

## Audit logging

Record event ID, UTC timestamp, request/correlation ID, tenant, actor, action, resource type/ID, decision, policy version, relevant detector reason codes, and minimal operational metadata. Hash or redact question text by default. Store audit data append-only with restricted read access and configured retention. Log at least authentication outcomes, upload/status transitions, policy changes, retrieval candidate/authorized counts, answer outcomes, citation resolution, admin actions, and security events.

## Threat controls

| Threat | Controls |
| --- | --- |
| Cross-tenant exposure | JWT-derived tenancy, row-level constraints, tenant predicates, application recheck |
| Stale policy | Policy versioning, short cache TTLs, recheck on retrieval and citation |
| Vector leakage | Metadata filtering plus authoritative post-filter; no direct index client access |
| Hallucinated sources | Structured citations validated against authorized chunk IDs |
| Upload abuse | Size/type/signature validation, scanning, rate limits, quarantine |
| Secret leakage | Detection/redaction before indexing; sensitive-log controls |
| Admin misuse | Least-privilege roles, audited changes, separation of duties where needed |
| Provider leakage | Minimum necessary redacted context, DPA/vendor review, configurable retention |

Before production, perform a formal threat model, penetration test, privacy/legal review, and incident-response tabletop exercise.

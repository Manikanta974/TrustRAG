# TrustRAG API contract

All API endpoints live under `/v1`, use JSON unless uploading a file, require `Authorization: Bearer <Supabase JWT>`, and return a `request_id`. FastAPI derives actor and tenant server-side. Error bodies must not reveal an unauthorized document’s existence.

## Common response shapes

```json
{ "request_id": "req_...", "error": { "code": "forbidden", "message": "You cannot access this resource." } }
```

Question outcomes are `answered`, `insufficient_evidence`, `blocked_security`, and `unavailable`. `401` means invalid/missing authentication; `403` means authenticated but not allowed; `404` is used where resource existence must be concealed; `422` means invalid input; `429` means rate limited.

## Employee endpoints

| Method | Path | Request | Response / rule |
| --- | --- | --- |
| `POST` | `/documents` | multipart PDF plus title and requested grants | Creates pending version; uploader must be authorized |
| `GET` | `/documents` | pagination/status filters | Lists only authorized documents |
| `GET` | `/documents/{document_id}` | — | Authorized metadata only |
| `POST` | `/questions` | question, optional conversation ID | Grounded answer/citations or safe outcome |
| `GET` | `/citations/{citation_id}` | — | Fresh access check; returns authorized source excerpt/location |

## Administrator endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `PATCH` | `/admin/documents/{document_id}/grants` | Replace/add/remove document grants; audit required |
| `GET` | `/admin/documents/{document_id}/access-preview` | Evaluate access for a selected user without exposing content |
| `GET` | `/admin/users` | User, role, and department management view |
| `PATCH` | `/admin/users/{user_id}` | Update application role/department membership |
| `GET` | `/admin/security-events` | Filtered security findings and audit events |
| `POST` | `/admin/documents/{document_id}/review` | Resolve quarantine/redaction review |
| `DELETE` | `/admin/documents/{document_id}` | Start governed deletion workflow |

## Question request and response

```json
{ "question": "What approval is required for client travel?", "conversation_id": "optional-uuid" }
```

```json
{
  "request_id": "req_01H...",
  "outcome": "answered",
  "answer": "Client travel requires manager approval before booking.",
  "citations": [{
    "citation_id": "cit_...",
    "document_id": "doc_...",
    "document_version_id": "ver_...",
    "chunk_id": "chk_...",
    "title": "Expense Policy",
    "location": { "page": 3, "section": "Travel approval" }
  }]
}
```

For `insufficient_evidence`, return a brief neutral message and `citations: []`; do not speculate. For `blocked_security`, return no retrieved content and a generic message. Models must return an internal structured schema (answer, claim-to-chunk mapping, confidence); the API validates it before constructing this public response.

## Contract rules for implementation

- Validate request size, MIME type, IDs, pagination bounds, and allowed filters with Pydantic.
- Avoid accepting `tenant_id`, `user_id`, roles, or authorization grants as unverified user-controlled context.
- Use idempotency keys for upload/delete operations.
- Never put raw JWTs, secrets, full document text, or raw sensitive query text in error responses.
- Version breaking API changes under a new path or negotiated contract.

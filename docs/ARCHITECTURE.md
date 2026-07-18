# TrustRAG architecture

## System overview

```text
Next.js + Tailwind browser app
          | Supabase Auth session
          v
FastAPI API  <---- verifies JWT / resolves tenant and user
  |     |\
  |     | \--> PostgreSQL + pgvector (documents, policies, chunks, audit)
  |     | \
  |     |  \-> Supabase Storage (private original PDFs)
  |     |
  |     \----> background ingestion worker (scan -> parse -> detect -> redact -> index)
  |
  \----------> provider abstraction (embeddings and LLM generation)
```

## Service responsibilities

| Component | Responsibility | Must not do |
| --- | --- | --- |
| Next.js web app | User/admin interfaces; sends bearer token; renders citations safely | Hold service-role keys or make security decisions |
| FastAPI | Validation, authorization, orchestration, response contracts, audit emission | Trust client-supplied tenant/user identifiers |
| PostgreSQL + pgvector | Policy data, metadata, chunk vectors, SQL metadata filters, audit data | Be treated as the sole authorization layer |
| Supabase Auth | User identity/session issuance | Determine document access policy by itself |
| Supabase Storage | Private original-file persistence | Serve public document URLs |
| Ingestion worker | Safe processing and index lifecycle | Mark unsafe/failed content retrievable |
| Provider adapter | Embeddings and structured grounded generation | Receive unauthorized or unredacted sensitive context |

## Request flows

### Ingestion

1. API authenticates uploader and authorizes upload for the tenant.
2. API records a `document` and immutable `document_version` in `pending` state, saves the original to a private storage path, and writes an audit event.
3. Worker validates file signature/type/size, scans it, parses with PyMuPDF, and detects injection, PII, and secrets.
4. Unsafe files are quarantined; no chunks or embeddings are activated. Policy/security events are emitted.
5. Safe content is normalized, redacted according to configured mode, chunked with page/offset provenance, embedded through the provider adapter, and inserted with tenant/document/version metadata.
6. The version becomes `ready` only after database transaction checks that chunks and access metadata are complete.

### Question answering

1. API validates Supabase JWT and derives tenant, user, role, and department claims/server-side memberships.
2. Query content is inspected for prompt injection, data-exfiltration intent, and abuse. The API blocks or continues with a security event.
3. API computes the caller’s effective access and performs pgvector search with mandatory tenant, `ready` version, and policy filters.
4. API revalidates each returned document/chunk against current policy; unauthorized candidates are discarded before reranking, logs, prompts, or streaming.
5. API sends only the final authorized context to the provider through a structured-output adapter.
6. API validates citations against the authorized chunk IDs. It refuses if evidence is absent, low-confidence, or the model output cannot be validated.
7. API records a privacy-minimized audit event and returns the answer, citations, outcome, and request ID.

## Provider abstraction

Define interfaces such as `EmbeddingProvider.embed(texts)` and `GenerationProvider.generateGroundedAnswer(question, chunks)`. Providers must be configured by environment, have timeouts/retries, and return no provider-specific types outside the adapter. Embedding model/version is persisted per chunk to support controlled reindexing.

## Deployment boundaries

Run web, API, and worker as separate deployable processes. Use a restricted database role for each service, a backend-only Supabase service key, private networking where available, and a managed secret store. Background work is queued rather than executed in request handlers. Design all processing and deletion operations to be idempotent.

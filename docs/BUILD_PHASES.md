# Build phases

Each phase has a narrow deliverable and verification gate. Do not start a later phase by weakening a prior phase’s security invariants.

## Phase 0 — Repository and local foundations

Create the monorepo layout, Python and Node toolchains, Docker/local PostgreSQL with pgvector, environment validation, linting/formatting, CI, and development documentation. No user-facing feature is required.

**Exit criteria:** fresh clone setup is documented; CI runs format, type checks, and empty test suites; no real credentials are committed.

## Phase 1 — Identity, tenancy, and authorization data

Integrate Supabase Auth; validate JWTs in FastAPI; create tenant, user profile, role, department, membership, document-policy, and audit schema migrations. Build server-side effective-access calculation and pytest coverage for every allow/deny combination.

**Exit criteria:** cross-tenant and non-member access are denied; policy changes are audited; API never trusts client tenant IDs.

## Phase 2 — Secure PDF ingestion

Implement private upload, status lifecycle, malware-scan integration point, PyMuPDF extraction, document/version metadata, chunking, PII/secret detection, prompt-injection inspection, quarantine, and idempotent workers.

**Exit criteria:** only safe, fully processed versions reach `ready`; a failed/quarantined version has no retrievable chunks; page provenance is preserved.

## Phase 3 — Permission-aware retrieval

Add pgvector migration and embeddings adapter. Implement tenant/policy-filtered hybrid retrieval, post-query authorization revalidation, result limits, and deletion/reindex workflows.

**Exit criteria:** adversarial tests prove unauthorized chunks never leave retrieval; revoked access takes effect on the next query; vector metadata cannot bypass application policy.

## Phase 4 — Grounded answers and citations

Implement generation adapter, injection-resistant system prompt, structured output schema, citation validation, refusal policy, answer/citation API, and privacy-minimized query audit records.

**Exit criteria:** every displayed citation belongs to authorized context; unsupported questions return `insufficient_evidence`; malformed provider output fails closed.

## Phase 5 — Web experience and administration

Build Next.js/Tailwind screens for sign-in, document upload/status, asking questions, citations, and the admin dashboard. Add role-gated routes and server/API enforcement behind every UI affordance.

**Exit criteria:** admins manage documents/users/policies/events; non-admin UI and API access are both denied; basic accessibility and Playwright smoke tests pass.

## Phase 6 — Hardening and release readiness

Add observability, rate limiting, retention and deletion controls, backup/recovery practice, load testing, threat-model review, dependency scanning, penetration testing, and evaluation corpus reporting.

**Exit criteria:** security review accepts residual risk; operational runbooks exist; metrics meet agreed quality, latency, and authorization-safety thresholds.

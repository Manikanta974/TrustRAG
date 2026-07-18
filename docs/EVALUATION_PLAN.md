# TrustRAG evaluation plan

## Objective

Prove that TrustRAG is secure before it is helpful, then measure grounded-answer quality, retrieval quality, and operational behavior using representative, permission-labeled enterprise data. Evaluation is a release gate, not a one-time demo.

## Test corpus

Create synthetic and approved sanitized documents spanning departments, overlapping terms, multiple versions, scanned/parse-failure PDFs, adversarial instructions, PII, secrets, and policy changes. Every chunk must have ground-truth tenant, document, version, source location, allowed users/departments/roles, and expected answerability labels. Never use unapproved production content in automated evaluation.

## Security evaluation

| Area | Method | Release expectation |
| --- | --- | --- |
| Tenant isolation | Same query across two tenants; direct-ID and vector-neighbor probes | Zero unauthorized chunks/citations |
| Access policy | Matrix of user, department, role, owner, revoked, inactive, and no-grant cases | 100% correct allow/deny decisions |
| Revocation | Change/remove grants between repeated queries | Next request cannot retrieve revoked content |
| Citation authorization | Resolve citations as allowed and disallowed users | Fresh authorization always enforced |
| Prompt injection | Query/document attack suite, encoded variants, indirect injection | Block/quarantine target met; no policy bypass |
| PII/secrets | Seeded detectors with benign near-matches | No high-confidence secret enters embeddings/prompts when policy requires redaction |

Any unauthorized context in a provider request, streamed token, citation, cache, or log is a release-blocking defect.

## Retrieval and answer evaluation

For each question, evaluate only against the user’s authorized ground-truth sources.

- **Authorized retrieval recall@k:** fraction of required authorized evidence retrieved.
- **Unauthorized retrieval rate:** unauthorized returned chunks / all returned chunks; target is exactly zero.
- **Citation precision:** cited chunks supporting claims / all cited chunks.
- **Citation coverage:** substantive claims with supporting citations / substantive claims.
- **Grounded answer correctness:** rubric-graded correctness against authorized evidence.
- **Refusal precision/recall:** correctly refuse unanswerable questions and answer supported ones.
- **Injection detection precision/recall:** track by severity and false-block cost.
- **Redaction precision/recall:** test secret/PII categories and offsets.

Set numerical thresholds with product/security owners after a baseline; security targets above are hard constraints, while quality thresholds are release criteria that improve by corpus iteration.

## Test layers

1. **Pytest unit tests:** policy evaluator, detector rules, redaction, chunk provenance, output validation.
2. **Integration tests:** FastAPI + disposable PostgreSQL/pgvector + Supabase test project/mocks; exercise migrations and retrieval filters.
3. **Adversarial regression suite:** known bypasses, injection samples, malformed files, and policy edge cases added for every incident.
4. **End-to-end tests:** Playwright later verifies sign-in, upload, permissions, admin pages, query/citation flows.
5. **Human evaluation:** security and domain reviewers score a sampled, de-identified answer set.

## Operational evaluation

Measure upload throughput, extraction failures, indexing latency, p50/p95 query latency, provider errors, vector query latency, detector latency, audit delivery, and cost per processed page/query. Run load tests with realistic tenant and permission cardinality. Test backup restore and document deletion propagation.

## Reporting and governance

Version the corpus, prompts, models, embedding model, detector rules, and evaluation code. Store aggregate results and redacted failures; restrict detailed failure artifacts. A release report must include security results, quality metrics, open risks, model/provider changes, and explicit approvers. Re-run affected suites after policy, retrieval, parser, model, or detector changes.

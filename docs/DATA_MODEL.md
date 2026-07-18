# TrustRAG data model

PostgreSQL is the system of record. All application tables include `tenant_id`, UUID primary keys, UTC `created_at`/`updated_at`, and foreign keys constrained to the same tenant where practical. Enable pgvector for chunk embeddings.

## Core entities

| Entity | Key fields | Notes |
| --- | --- | --- |
| `tenants` | `id`, `name`, `status` | Organization boundary |
| `users` | `id`, `tenant_id`, `supabase_user_id`, `email`, `status` | Maps verified identity to application tenant |
| `roles` | `id`, `tenant_id`, `name` | e.g. employee, manager, security_admin, platform_admin |
| `user_roles` | `user_id`, `role_id` | Many-to-many, effective-dated if required |
| `departments` | `id`, `tenant_id`, `name` | Department access principal |
| `department_memberships` | `user_id`, `department_id` | Active membership is required for a grant |
| `documents` | `id`, `tenant_id`, `owner_user_id`, `title`, `status` | Logical document across versions |
| `document_versions` | `id`, `document_id`, `version_number`, `storage_key`, `sha256`, `status` | Immutable upload/extraction lifecycle |
| `document_access_grants` | `document_id`, `principal_type`, `principal_id`, `permission` | `principal_type`: user, department, role; first permission is `read` |
| `document_chunks` | `id`, `tenant_id`, `document_version_id`, `content`, `embedding`, `page_number`, `start_offset`, `end_offset` | Only ready versions are searched |
| `security_findings` | `id`, `tenant_id`, `resource_type`, `resource_id`, `detector`, `severity`, `reason_code`, `status` | Never store detected secret plaintext |
| `audit_events` | `id`, `tenant_id`, `actor_user_id`, `action`, `resource`, `decision`, `metadata`, `occurred_at` | Append-only operational record |
| `question_requests` | `id`, `tenant_id`, `user_id`, `question_hash`, `outcome`, `model_config` | Store raw text only under approved retention policy |
| `answer_citations` | `question_request_id`, `chunk_id`, `claim_index` | Immutable answer provenance |

## Required statuses

`document_versions.status`: `pending`, `scanning`, `processing`, `ready`, `quarantined`, `failed`, `deleted`.

Only versions with `ready` status are eligible for retrieval. `documents.status` supports `active`, `deleted`, and `archived`; it is an additional filter, not a substitute for version status.

## Access query shape

At retrieval time, derive principals from the authenticated user, then apply all predicates:

```sql
chunk.tenant_id = :tenant_id
AND document.status = 'active'
AND version.status = 'ready'
AND EXISTS (matching active user, department, role, or owner grant)
```

Apply these filters before vector ranking. Revalidate returned IDs in application code. Use indexes on tenant/status/version joins and an appropriate pgvector index after measuring recall/latency. Never use a global nearest-neighbor query followed only by client-side filtering.

## Deletion and retention

Document deletion is a stateful, idempotent workflow: revoke retrieval immediately, remove chunks/embeddings, remove storage object according to retention/legal-hold policy, then record final state and audit event. Retain the minimum audit metadata necessary to prove the action without retaining document content.

## Migration guidance

Use version-controlled SQL/Alembic migrations. Enable Row Level Security where Supabase access patterns benefit from it, but do not rely on RLS alone: FastAPI remains the policy enforcement point. Seed data must contain synthetic identities and documents only.

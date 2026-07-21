# TrustRAG data model

PostgreSQL is the system of record. All application tables include `organization_id`, UUID primary keys, UTC `created_at`/`updated_at`, and foreign keys constrained to the same organization where practical. Enable pgvector for chunk embeddings.

## Core entities

| Entity | Key fields | Notes |
| --- | --- | --- |
| `organizations` | `id`, `name`, `status` | Organization boundary (tenant) |
| `profiles` | `id`, `organization_id`, `supabase_user_id`, `email`, `status` | Maps verified identity to application organization |
| `organization_roles` | `id`, `organization_id`, `name`, `display_name`, `description` | Per-organization role catalog; also a document_acl principal_type target |
| `organization_memberships` | `id`, `organization_id`, `profile_id`, `role_id`, `status` | Role grant, referencing `organization_roles` |
| `departments` | `id`, `organization_id`, `name` | Department access principal |
| `department_memberships` | `id`, `organization_id`, `department_id`, `profile_id`, `status` | Active membership is required for a grant |
| `groups` | `id`, `organization_id`, `name` | Ad-hoc access principal distinct from department/role grants |
| `group_members` | `id`, `organization_id`, `group_id`, `profile_id` | Group membership |
| `documents` | `id`, `organization_id`, `owner_profile_id`, `title`, `status`, `classification` | Logical document across versions |
| `document_versions` | `id`, `organization_id`, `document_id`, `version_number`, `storage_key`, `sha256`, `status` | Immutable upload/extraction lifecycle |
| `document_acl` | `id`, `organization_id`, `document_id`, `principal_type`, `principal_id`, `permission` | `principal_type`: user, department, group, role; `principal_id` references `profiles`/`departments`/`groups`/`organization_roles` accordingly; first permission is `read` |
| `document_chunks` | `id`, `organization_id`, `document_version_id`, `content`, `embedding`, `embedding_model`, `embedding_version`, `page_number`, `start_offset`, `end_offset` | Only ready versions are searched |
| `conversations` | `id`, `organization_id`, `profile_id`, `title` | Groups related question/answer turns |
| `messages` | `id`, `organization_id`, `conversation_id`, `role`, `content` | `role`: user, assistant, system |
| `query_runs` | `id`, `organization_id`, `profile_id`, `conversation_id`, `question_hash`, `outcome`, `model_config` | Store raw text only under approved retention policy |
| `query_sources` | `id`, `organization_id`, `query_run_id`, `chunk_id`, `claim_index` | Immutable answer provenance |
| `security_events` | `id`, `organization_id`, `resource_type`, `resource_id`, `detector`, `severity`, `reason_code`, `status` | Never store detected secret plaintext |
| `audit_events` | `id`, `organization_id`, `actor_profile_id`, `action`, `resource_type`, `resource_id`, `decision`, `policy_version`, `metadata`, `occurred_at` | Append-only operational record |

## Required statuses

`document_versions.status`: `pending`, `scanning`, `processing`, `ready`, `quarantined`, `failed`, `deleted`.

Only versions with `ready` status are eligible for retrieval. `documents.status` supports `active`, `deleted`, and `archived`; it is an additional filter, not a substitute for version status.

## Access query shape

At retrieval time, derive principals from the authenticated user, then apply all predicates:

```sql
chunk.organization_id = :organization_id
AND document.status = 'active'
AND version.status = 'ready'
AND EXISTS (matching active user, department, group, role, or owner grant)
```

Apply these filters before vector ranking. Revalidate returned IDs in application code. Use indexes on organization/status/version joins and an appropriate pgvector index after measuring recall/latency. Never use a global nearest-neighbor query followed only by client-side filtering.

## Deletion and retention

Document deletion is a stateful, idempotent workflow: revoke retrieval immediately, remove chunks/embeddings, remove storage object according to retention/legal-hold policy, then record final state and audit event. Retain the minimum audit metadata necessary to prove the action without retaining document content.

## Migration guidance

Use version-controlled SQL/Alembic migrations. Enable Row Level Security where Supabase access patterns benefit from it, but do not rely on RLS alone: FastAPI remains the policy enforcement point. Seed data must contain synthetic identities and documents only.

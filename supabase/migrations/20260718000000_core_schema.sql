-- TrustRAG core schema (Phase 1/2 foundation)
--
-- Security assumptions enforced by this schema (see docs/SECURITY_MODEL.md):
--   * Authorization is evaluated in the application before retrieval; this schema only
--     stores the grants (document_acl, department_memberships, group_members,
--     organization_memberships) that FastAPI must re-check on every query and citation.
--   * The LLM never decides access. No table here is readable by a model directly;
--     access decisions are computed server-side from these tables before any prompt.
--   * Documents/chunks are untrusted data, never instructions. document_chunks.content
--     is retrieved text only and must never be interpreted as directives during generation.
--
-- This migration intentionally contains no Row Level Security policies and no seed data.

begin;

create extension if not exists pgcrypto;
create extension if not exists vector;

-- ---------------------------------------------------------------------------
-- Tenancy and identity
-- ---------------------------------------------------------------------------

create table organizations (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    status text not null default 'active'
        check (status in ('active', 'suspended', 'deleted')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- profiles.organization_id is the user's single home tenant; TrustRAG does not
-- support cross-tenant sharing (docs/PROJECT_SPEC.md non-goals).
-- supabase_user_id maps to a Supabase Auth user id (auth.users.id) at the
-- application layer; no DB-level FK to auth.users is declared here so this
-- schema applies cleanly on plain local Postgres. Supabase-specific RLS and
-- auth policies binding this column will be added in a later migration.
create table profiles (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    supabase_user_id uuid not null unique,
    email text not null,
    status text not null default 'active'
        check (status in ('active', 'inactive', 'deleted')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_profiles_organization_id on profiles (organization_id);
create index idx_profiles_status on profiles (status);

-- Roles are data, scoped per organization, so both organization_memberships and
-- document_acl (principal_type = 'role') can reference a real row instead of a
-- fixed/enumerated value. Seed or admin tooling is expected to provision the
-- baseline roles (e.g. admin, manager, employee, intern) per organization.
create table organization_roles (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    name text not null,
    display_name text,
    description text,
    created_at timestamptz not null default now(),
    unique (organization_id, name)
);

create index idx_organization_roles_organization_id on organization_roles (organization_id);

-- Role grants are always scoped to one organization membership; an application
-- role never implies access outside the caller's own organization. role_id must
-- reference an organization_roles row of the same organization_id; FastAPI
-- validates this on write since it spans two FKs rather than one composite key.
create table organization_memberships (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    profile_id uuid not null references profiles (id) on delete cascade,
    role_id uuid not null references organization_roles (id),
    status text not null default 'active'
        check (status in ('active', 'revoked')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (organization_id, profile_id, role_id)
);

create index idx_org_memberships_organization_id on organization_memberships (organization_id);
create index idx_org_memberships_profile_id on organization_memberships (profile_id);
create index idx_org_memberships_role_id on organization_memberships (role_id);
create index idx_org_memberships_status on organization_memberships (status);

create table departments (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    name text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (organization_id, name)
);

create index idx_departments_organization_id on departments (organization_id);

-- Required for the "matching department grant" access predicate in
-- docs/DATA_MODEL.md; not a random addition beyond documented scope.
create table department_memberships (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    department_id uuid not null references departments (id) on delete cascade,
    profile_id uuid not null references profiles (id) on delete cascade,
    status text not null default 'active'
        check (status in ('active', 'revoked')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (department_id, profile_id)
);

create index idx_department_memberships_organization_id on department_memberships (organization_id);
create index idx_department_memberships_department_id on department_memberships (department_id);
create index idx_department_memberships_profile_id on department_memberships (profile_id);
create index idx_department_memberships_status on department_memberships (status);

-- Ad-hoc access principal (e.g. a cross-department project team) distinct from
-- department and role grants; used only as a document_acl principal_type.
create table groups (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    name text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (organization_id, name)
);

create index idx_groups_organization_id on groups (organization_id);

create table group_members (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    group_id uuid not null references groups (id) on delete cascade,
    profile_id uuid not null references profiles (id) on delete cascade,
    created_at timestamptz not null default now(),
    unique (group_id, profile_id)
);

create index idx_group_members_organization_id on group_members (organization_id);
create index idx_group_members_group_id on group_members (group_id);
create index idx_group_members_profile_id on group_members (profile_id);

-- ---------------------------------------------------------------------------
-- Documents
-- ---------------------------------------------------------------------------

create table documents (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    owner_profile_id uuid not null references profiles (id),
    title text not null,
    status text not null default 'active'
        check (status in ('active', 'archived', 'deleted')),
    -- Additive classification hook per docs/SECURITY_MODEL.md; does not by
    -- itself grant access and does not weaken the default-deny grant check.
    classification text not null default 'internal'
        check (classification in ('public', 'internal', 'confidential', 'restricted')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_documents_organization_id on documents (organization_id);
create index idx_documents_status on documents (status);

-- Immutable per docs/DATA_MODEL.md: a new upload creates a new version row,
-- never overwrites a prior one. Only status = 'ready' is ever retrievable.
create table document_versions (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    document_id uuid not null references documents (id) on delete cascade,
    version_number integer not null,
    storage_key text not null,
    sha256 text not null,
    status text not null default 'pending'
        check (status in ('pending', 'scanning', 'processing', 'ready', 'quarantined', 'failed', 'deleted')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (document_id, version_number)
);

create index idx_document_versions_organization_id on document_versions (organization_id);
create index idx_document_versions_document_id on document_versions (document_id);
create index idx_document_versions_status on document_versions (status);

-- Polymorphic grant: principal_id refers to profiles.id, departments.id,
-- groups.id, or organization_roles.id depending on principal_type. No DB-level
-- FK is possible across those targets; FastAPI must validate principal
-- existence and re-check this table on every retrieval and citation
-- resolution, never trust it as a cached decision.
create table document_acl (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    document_id uuid not null references documents (id) on delete cascade,
    principal_type text not null
        check (principal_type in ('user', 'department', 'group', 'role')),
    principal_id uuid not null,
    permission text not null default 'read'
        check (permission in ('read')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (document_id, principal_type, principal_id, permission)
);

create index idx_document_acl_organization_id on document_acl (organization_id);
create index idx_document_acl_document_id on document_acl (document_id);
create index idx_document_acl_principal on document_acl (principal_type, principal_id);

-- Embedding dimension (1536) matches common OpenAI-compatible embedding models
-- and is provisional pending final provider selection (docs/ARCHITECTURE.md
-- provider abstraction); revisit via a follow-up migration if it changes.
--
-- Only chunks belonging to a document_version with status = 'ready' may ever
-- be selected for retrieval; that predicate is enforced in application SQL,
-- not by this table alone (docs/DATA_MODEL.md access query shape).
create table document_chunks (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    document_version_id uuid not null references document_versions (id) on delete cascade,
    content text not null,
    embedding vector(1536),
    embedding_model text,
    embedding_version text,
    page_number integer,
    start_offset integer,
    end_offset integer,
    created_at timestamptz not null default now()
);

create index idx_document_chunks_organization_id on document_chunks (organization_id);
create index idx_document_chunks_document_version_id on document_chunks (document_version_id);
create index idx_document_chunks_embedding on document_chunks
    using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ---------------------------------------------------------------------------
-- Conversations and grounded question answering
-- ---------------------------------------------------------------------------

create table conversations (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    profile_id uuid not null references profiles (id) on delete cascade,
    title text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_conversations_organization_id on conversations (organization_id);
create index idx_conversations_profile_id on conversations (profile_id);

-- content is untrusted data end to end, whether role = 'user' (the question)
-- or role = 'assistant' (model output already validated against authorized
-- chunk IDs); it is never re-interpreted as an instruction on replay.
create table messages (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    conversation_id uuid not null references conversations (id) on delete cascade,
    role text not null
        check (role in ('user', 'assistant', 'system')),
    content text not null,
    created_at timestamptz not null default now()
);

create index idx_messages_organization_id on messages (organization_id);
create index idx_messages_conversation_id on messages (conversation_id);
create index idx_messages_created_at on messages (created_at);

-- One row per answered question. outcome is the machine-readable result
-- contract from docs/API_CONTRACT.md; 'blocked_security' and
-- 'insufficient_evidence' must never carry retrieved content in question_hash
-- adjacent fields beyond what policy allows.
create table query_runs (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    profile_id uuid not null references profiles (id) on delete cascade,
    conversation_id uuid references conversations (id) on delete set null,
    question_hash text not null,
    outcome text not null
        check (outcome in ('answered', 'insufficient_evidence', 'blocked_security', 'unavailable')),
    model_config jsonb,
    created_at timestamptz not null default now()
);

create index idx_query_runs_organization_id on query_runs (organization_id);
create index idx_query_runs_profile_id on query_runs (profile_id);
create index idx_query_runs_outcome on query_runs (outcome);
create index idx_query_runs_created_at on query_runs (created_at);

-- Citations are validated against the authorized retrieval set before being
-- persisted; a query_source row must never reference a chunk the caller was
-- not authorized to see at answer time.
create table query_sources (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    query_run_id uuid not null references query_runs (id) on delete cascade,
    chunk_id uuid not null references document_chunks (id),
    claim_index integer not null,
    created_at timestamptz not null default now()
);

create index idx_query_sources_organization_id on query_sources (organization_id);
create index idx_query_sources_query_run_id on query_sources (query_run_id);
create index idx_query_sources_chunk_id on query_sources (chunk_id);

-- ---------------------------------------------------------------------------
-- Security and audit
-- ---------------------------------------------------------------------------

-- Never store detected secret/PII plaintext here; reason_code and severity
-- only (docs/SECURITY_MODEL.md).
create table security_events (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    resource_type text not null,
    resource_id uuid,
    detector text not null,
    severity text not null
        check (severity in ('low', 'medium', 'high', 'critical')),
    reason_code text,
    status text not null default 'open'
        check (status in ('open', 'reviewed', 'resolved', 'dismissed')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_security_events_organization_id on security_events (organization_id);
create index idx_security_events_severity on security_events (severity);
create index idx_security_events_status on security_events (status);
create index idx_security_events_created_at on security_events (created_at);

-- Append-only by convention: no update/delete path is granted at the
-- application layer. decision records the authorization outcome for the
-- audited action, independent of any LLM output.
create table audit_events (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations (id) on delete cascade,
    actor_profile_id uuid references profiles (id),
    action text not null,
    resource_type text not null,
    resource_id uuid,
    decision text not null
        check (decision in ('allow', 'deny')),
    policy_version text,
    metadata jsonb,
    occurred_at timestamptz not null default now()
);

create index idx_audit_events_organization_id on audit_events (organization_id);
create index idx_audit_events_actor_profile_id on audit_events (actor_profile_id);
create index idx_audit_events_decision on audit_events (decision);
create index idx_audit_events_occurred_at on audit_events (occurred_at);

commit;

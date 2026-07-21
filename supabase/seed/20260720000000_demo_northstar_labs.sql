-- TrustRAG demo seed data: fictional organization "Northstar Labs".
-- Synthetic identities and documents only; no production content (docs/DATA_MODEL.md).
-- All rows use fixed UUIDs and INSERT ... ON CONFLICT (id) DO NOTHING for repeatable re-application.
--
-- Roles (admin, manager, employee, intern) are real organization_roles rows,
-- referenced by organization_memberships.role_id and by document_acl rows with
-- principal_type = 'role' (principal_id = organization_roles.id). No fake/enumerated
-- role values are used.

begin;

-- ---------------------------------------------------------------------------
-- Organization
-- ---------------------------------------------------------------------------

insert into organizations (id, name, slug, status)
values ('10000000-0000-0000-0000-000000000001', 'Northstar Labs', 'northstar-labs', 'active')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Organization roles
-- ---------------------------------------------------------------------------

insert into organization_roles (id, organization_id, name, display_name, description) values
    ('d0000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'admin', 'Admin', 'Platform administrator with full organization access'),
    ('d0000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', 'manager', 'Manager', 'Department manager with scoped administrative access'),
    ('d0000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', 'employee', 'Employee', 'Standard employee access'),
    ('d0000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000001', 'intern', 'Intern', 'Time-limited restricted employee access')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Departments
-- ---------------------------------------------------------------------------

insert into departments (id, organization_id, name) values
    ('30000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'Engineering'),
    ('30000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', 'HR'),
    ('30000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', 'Finance'),
    ('30000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000001', 'Legal'),
    ('30000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000001', 'Product')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Profiles (supabase_user_id is a synthetic stand-in; see migration comment)
-- ---------------------------------------------------------------------------

insert into profiles (id, organization_id, supabase_user_id, email, status) values
    ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '21000000-0000-0000-0000-000000000001', 'admin@northstarlabs.demo', 'active'),
    ('20000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '21000000-0000-0000-0000-000000000002', 'manager@northstarlabs.demo', 'active'),
    ('20000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '21000000-0000-0000-0000-000000000003', 'engineer@northstarlabs.demo', 'active'),
    ('20000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000001', '21000000-0000-0000-0000-000000000004', 'employee@northstarlabs.demo', 'active'),
    ('20000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000001', '21000000-0000-0000-0000-000000000005', 'intern@northstarlabs.demo', 'active')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Organization memberships (role grants)
-- ---------------------------------------------------------------------------

insert into organization_memberships (id, organization_id, profile_id, role_id, status) values
    ('40000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', 'active'),
    ('40000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000002', 'd0000000-0000-0000-0000-000000000002', 'active'),
    ('40000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000003', 'd0000000-0000-0000-0000-000000000003', 'active'),
    ('40000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000004', 'd0000000-0000-0000-0000-000000000003', 'active'),
    ('40000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000005', 'd0000000-0000-0000-0000-000000000004', 'active')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Department memberships
-- ---------------------------------------------------------------------------

insert into department_memberships (id, organization_id, department_id, profile_id, status) values
    ('50000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000003', 'active'),
    ('50000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000004', 'active'),
    ('50000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000005', 'active')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Groups and group memberships
-- ---------------------------------------------------------------------------

insert into groups (id, organization_id, name) values
    ('60000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'Engineering Team'),
    ('60000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', 'HR Team'),
    ('60000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', 'Finance Reviewers'),
    ('60000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000001', 'Legal Reviewers')
on conflict (id) do nothing;

insert into group_members (id, organization_id, group_id, profile_id) values
    ('70000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '60000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000003'),
    ('70000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '60000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000005'),
    ('70000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '60000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000004'),
    ('70000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000001', '60000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000002'),
    ('70000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000001', '60000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000001')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Documents and versions
-- ---------------------------------------------------------------------------

insert into documents (id, organization_id, owner_profile_id, title, status, classification) values
    ('80000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'Employee Handbook', 'active', 'internal'),
    ('80000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'Leave Policy', 'active', 'internal'),
    ('80000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000003', 'Engineering Architecture Overview', 'active', 'confidential'),
    ('80000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000002', 'Salary Bands 2026', 'active', 'restricted'),
    ('80000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'Legal Contract', 'active', 'restricted'),
    ('80000000-0000-0000-0000-000000000006', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'Malicious Prompt Injection Test Document', 'active', 'internal')
on conflict (id) do nothing;

-- Only version 6 is 'quarantined': demonstrates that a quarantined version has
-- no retrievable chunks regardless of any document_acl grant (docs/BUILD_PHASES.md Phase 2 exit criteria).
insert into document_versions (id, organization_id, document_id, version_number, storage_key, sha256, original_filename, mime_type, file_size_bytes, status) values
    ('81000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000001', 1, 'northstar-labs/documents/employee-handbook/v1.pdf', encode(digest('employee-handbook-v1', 'sha256'), 'hex'), 'employee-handbook.pdf', 'application/pdf', 245000, 'ready'),
    ('81000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000002', 1, 'northstar-labs/documents/leave-policy/v1.pdf', encode(digest('leave-policy-v1', 'sha256'), 'hex'), 'leave-policy.pdf', 'application/pdf', 98000, 'ready'),
    ('81000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000003', 1, 'northstar-labs/documents/engineering-architecture-overview/v1.pdf', encode(digest('engineering-architecture-overview-v1', 'sha256'), 'hex'), 'engineering-architecture-overview.pdf', 'application/pdf', 512000, 'ready'),
    ('81000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000004', 1, 'northstar-labs/documents/salary-bands-2026/v1.pdf', encode(digest('salary-bands-2026-v1', 'sha256'), 'hex'), 'salary-bands-2026.pdf', 'application/pdf', 64000, 'ready'),
    ('81000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000005', 1, 'northstar-labs/documents/legal-contract/v1.pdf', encode(digest('legal-contract-v1', 'sha256'), 'hex'), 'legal-contract.pdf', 'application/pdf', 187000, 'ready'),
    ('81000000-0000-0000-0000-000000000006', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000006', 1, 'northstar-labs/documents/malicious-prompt-injection-test-document/v1.pdf', encode(digest('malicious-prompt-injection-test-document-v1', 'sha256'), 'hex'), 'malicious-prompt-injection-test-document.pdf', 'application/pdf', 15000, 'quarantined')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Document ACL
-- Covers all principal_type values: role, department, group, and an explicit
-- user restriction alongside a group grant. Document 6 (quarantined) has
-- intentionally no ACL rows: it must stay unreachable regardless of grants.
-- ---------------------------------------------------------------------------

insert into document_acl (id, organization_id, document_id, principal_type, principal_id, permission) values
    ('90000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000001', 'role', 'd0000000-0000-0000-0000-000000000003', 'read'),
    ('90000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000002', 'role', 'd0000000-0000-0000-0000-000000000003', 'read'),
    ('90000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000003', 'department', '30000000-0000-0000-0000-000000000001', 'read'),
    ('90000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000004', 'group', '60000000-0000-0000-0000-000000000003', 'read'),
    ('90000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000004', 'user', '20000000-0000-0000-0000-000000000001', 'read'),
    ('90000000-0000-0000-0000-000000000006', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000005', 'group', '60000000-0000-0000-0000-000000000004', 'read'),
    ('90000000-0000-0000-0000-000000000007', '10000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000005', 'role', 'd0000000-0000-0000-0000-000000000001', 'read')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Document chunks (demo metadata only; no real embeddings)
-- Only 'ready' versions get chunks. Document 6 (quarantined) has none.
-- ---------------------------------------------------------------------------

insert into document_chunks (id, organization_id, document_version_id, content, page_number, start_offset, end_offset) values
    ('a1000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '81000000-0000-0000-0000-000000000001', 'Northstar Labs expects all employees to act with integrity and follow the code of conduct.', 1, 0, 92),
    ('a1000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '81000000-0000-0000-0000-000000000002', 'Full-time employees accrue 15 days of paid leave per year, requestable through the HR portal.', 1, 0, 95),
    ('a1000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '81000000-0000-0000-0000-000000000003', 'The platform is composed of a Next.js frontend, a FastAPI backend, and a PostgreSQL/pgvector store.', 1, 0, 99),
    ('a1000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000001', '81000000-0000-0000-0000-000000000004', 'Engineering Level 3 salary band for fiscal year 2026 is confidential and reviewed annually by Finance.', 1, 0, 103),
    ('a1000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000001', '81000000-0000-0000-0000-000000000005', 'This agreement is confidential and governs the vendor relationship between Northstar Labs and its counterparty.', 1, 0, 111)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Security events
-- ---------------------------------------------------------------------------

insert into security_events (id, organization_id, resource_type, resource_id, detector, severity, reason_code, status) values
    ('b1000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'document_version', '81000000-0000-0000-0000-000000000006', 'prompt_injection_heuristics', 'critical', 'instruction_override_attempt', 'open'),
    ('b1000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', 'document_version', '81000000-0000-0000-0000-000000000004', 'pii_secret_scanner', 'medium', 'possible_compensation_data', 'resolved')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Audit events
-- ---------------------------------------------------------------------------

insert into audit_events (id, organization_id, actor_profile_id, action, resource_type, resource_id, decision, policy_version, occurred_at) values
    ('c1000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'document.upload', 'document', '80000000-0000-0000-0000-000000000006', 'allow', 'v1', now()),
    ('c1000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', null, 'document_version.quarantine', 'document_version', '81000000-0000-0000-0000-000000000006', 'deny', 'v1', now()),
    ('c1000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000002', 'document_acl.grant', 'document', '80000000-0000-0000-0000-000000000004', 'allow', 'v1', now())
on conflict (id) do nothing;

commit;

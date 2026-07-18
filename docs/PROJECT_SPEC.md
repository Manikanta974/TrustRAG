# TrustRAG project specification

## Purpose

TrustRAG is an internal document-intelligence system for organizations. It answers natural-language questions from private company documents, but only from material the signed-in user is currently authorized to access. It is not a general chatbot, web-search product, or autonomous agent.

## Core goals

1. Secure document upload, parsing, chunking, and indexing.
2. Role-based and department-based document access.
3. Permission-aware vector retrieval before LLM generation.
4. Citation-backed, source-verifiable answers.
5. Refusal when authorized evidence is insufficient.
6. Prompt-injection detection for questions and uploaded documents.
7. PII and secret detection with redaction controls.
8. Tamper-resistant audit logging.
9. An admin dashboard for documents, users, permissions, and security events.

## Actors

| Actor | Responsibilities | Permissions |
| --- | --- | --- |
| Employee | Upload permitted documents; ask questions; inspect authorized citations | Read documents granted by policy; create own queries |
| Document owner | Manage a document’s metadata and access policy | Owner actions on assigned documents |
| Department manager | Review department documents and membership-related access | Scoped administrative actions |
| Security administrator | Review alerts, detections, audit trails, retention actions | Security event and policy administration |
| Platform administrator | Configure tenants, roles, integrations, and global settings | Highest privileged, audited actions |

## Functional requirements

### Documents

- Support PDF upload in the first release; validate MIME type, file signature, size, and malware-scan status before extraction.
- Store originals privately in Supabase Storage; do not use public buckets or public URLs.
- Create immutable document versions. A new upload replaces no historical record; it creates a new version and changes active-version status.
- Parse PDFs through PyMuPDF, preserve page numbers, normalize text, chunk deterministically, and retain source offsets.
- Classify extraction/indexing status (`pending`, `scanning`, `processing`, `ready`, `quarantined`, `failed`, `deleted`). Only `ready` material is retrievable.

### Access control

- Authenticate through Supabase Auth and validate JWTs in FastAPI.
- Resolve access from tenant membership, application role, department membership, document owner, explicit user grants, and document-level department grants.
- Default deny. A match on tenant plus an active policy grant is required; classification/clearance support may be added without weakening this rule.
- Evaluate access again when resolving a citation or download, not only at query time.

### Questions and answers

- Accept a question from an authenticated employee within one tenant.
- Detect unsafe or injection-like content before retrieval. Block or require review according to severity.
- Retrieve only chunks whose active document version is authorized for that user. Filter in SQL/vector query and revalidate in application code.
- Send only authorized, sanitized chunks to the LLM provider.
- Require structured answer output containing claims and chunk IDs. Validate IDs against the actual authorized retrieval set.
- Return answer text, citations, a request ID, and a machine-readable outcome (`answered`, `insufficient_evidence`, `blocked_security`, `unavailable`).

### Administrative dashboard

- Documents: status, owner, version, departments/users granted access, sensitivity findings, ingestion errors, deletion controls.
- Users: synced identity, role, department memberships, active/inactive status.
- Permissions: policy editor, preview/effective-access view, change history.
- Security events: prompt-injection, PII/secret detections, policy denials, ingestion quarantine, and audit search.

## Explicit non-goals for the initial product

- Autonomous execution in other company systems.
- Public web retrieval or blending external sources into private answers.
- LLM-controlled authorization, tool calls, or policy changes.
- Cross-tenant sharing.
- Support for arbitrary file types before their parsing and threat model are implemented.

## Definition of done for the first usable release

A signed-in, authorized employee can upload a safe PDF, assign authorized departments/users, ask a benign question, receive an answer with page-level citations from only allowed documents, and see a refusal for unsupported questions. An administrator can audit all related actions and review security detections.

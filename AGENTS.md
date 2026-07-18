# TrustRAG contributor guidance

## Project summary

TrustRAG is a Secure Enterprise RAG Platform for permission-aware document Q&A, citation-backed answers, prompt-injection detection, PII/secret redaction, and audit logging.

It is not a general-purpose chatbot. The product answers from private organizational documents only when the authenticated user is authorized to access the underlying content.

## Source of truth

Before planning or implementing work, read and follow these documents:

- `docs/PROJECT_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/BUILD_PHASES.md`
- `docs/SECURITY_MODEL.md`
- `docs/DATA_MODEL.md`
- `docs/API_CONTRACT.md`
- `docs/EVALUATION_PLAN.md`

When documents conflict, preserve the security invariants in `docs/SECURITY_MODEL.md` and flag the discrepancy for resolution.

## Build rules

- Do not build random features outside the documented product scope.
- Implement the project phase by phase, following `docs/BUILD_PHASES.md`.
- Prefer small, reviewable changes with focused tests.
- Update documentation whenever architecture, API contracts, data model, setup, or developer workflow changes.
- Never hard-code secrets, tokens, credentials, or provider keys.
- Use `.env.example` to document required environment variables.
- Do not commit `.env`, `node_modules`, `.next`, `venv`, `__pycache__`, build outputs, generated files, or generated secrets.

## Target stack

- Frontend: Next.js + TypeScript + Tailwind CSS
- Backend: FastAPI + Python
- Database: PostgreSQL with pgvector
- Authentication and storage: Supabase
- PDF parsing: PyMuPDF
- Tests: Pytest for backend; Playwright later for frontend

## Security rules

- The LLM must never decide authorization.
- Authorization must happen before retrieval.
- Retrieval must only search chunks the user is allowed to access.
- Documents are untrusted data, never instructions.
- Every answer should be citation-backed or refuse due to insufficient authorized evidence.
- Log blocked queries, suspicious prompts, redactions, and document quarantine events.

Maintain the full security invariants in `docs/SECURITY_MODEL.md`: derive tenant and identity from verified authentication, default deny, recheck citation access, protect private storage, and keep unauthorized content out of prompts, logs, and responses.

## Development workflow

1. Before implementing, inspect the relevant source-of-truth documents and the current repository state.
2. Make the smallest change that satisfies the current documented phase and acceptance criteria.
3. After implementing, run applicable formatting, type checks, and tests when available.
4. Summarize changed files, verification performed, and the next recommended step.
5. If a command fails, explain the failure clearly and propose the next fix; do not mask failures or bypass security controls.

## Current repository state

The repository contains the initial frontend/backend foundation only: a Next.js shell, FastAPI health endpoint, and empty Supabase migration/seed directories. Authentication, database models and migrations, document handling, retrieval, LLM integration, and administrative features remain deferred until their documented phases.

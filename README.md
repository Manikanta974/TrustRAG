# TrustRAG

TrustRAG is a secure enterprise RAG platform for internal documents. It lets authenticated employees upload and query private knowledge while enforcing role- and department-based access **before retrieval and LLM generation**. Every answer is grounded in authorized source material, cited, audited, and refused when evidence is insufficient.

This repository contains the Phase 1 foundation: a Next.js frontend shell, a FastAPI health-check service, and placeholders for future Supabase migrations/seeds. Authentication, persistence, document handling, RAG, and LLM integrations are intentionally not implemented yet.

## Target stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python |
| Database and vector search | PostgreSQL with pgvector |
| Authentication and object storage | Supabase Auth and Supabase Storage |
| Document parsing | PyMuPDF |
| LLM and embeddings | Provider abstraction; initially OpenAI-compatible APIs |
| Tests | Pytest for backend; Playwright in a later frontend phase |

## Non-negotiable product rules

1. Authorization is evaluated before candidate chunks enter reranking, prompts, logs, or responses.
2. Every durable derived artifact retains tenant, document, version, and access metadata.
3. Models cannot make authorization decisions or cite content outside the authorized retrieval set.
4. Insufficient authorized evidence produces a refusal, never an ungrounded answer.
5. Uploads, queries, policy changes, retrieval decisions, and security detections are auditable.

## Planning documents

- [Project specification](docs/PROJECT_SPEC.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Build phases](docs/BUILD_PHASES.md)
- [Security model](docs/SECURITY_MODEL.md)
- [Data model](docs/DATA_MODEL.md)
- [API contract](docs/API_CONTRACT.md)
- [Evaluation plan](docs/EVALUATION_PLAN.md)

## Future repository shape

```text
apps/web/              Next.js + TypeScript + Tailwind frontend shell
services/api/          FastAPI service foundation and pytest health test
supabase/migrations/   Future version-controlled database migrations
supabase/seed/         Future synthetic development seed data
docs/                  Product and implementation context
```

## Local setup

Prerequisites: Node.js 20.9+, Python 3.11+, and optionally Docker for the future local pgvector placeholder.

1. Copy `.env.example` to `.env`. It contains placeholders only; do not add real secrets to version control.
2. Install frontend dependencies from the repository root:

   ```bash
   npm install
   npm run dev:web
   ```

   The web shell runs at `http://localhost:3000` by default.

3. Set up and run the backend from `services/api`:

   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"
   python -m uvicorn app.main:app --reload --port 8000
   ```

   Check `http://localhost:8000/health`; it returns `{"status":"ok","service":"trustrag-api"}`.

4. Run the current backend checks:

   ```bash
   python -m pytest
   python -m ruff check app
   ```

`docker compose up postgres` starts an empty local pgvector-enabled PostgreSQL placeholder. No app service uses it yet, and no Supabase/Auth/Storage services are configured at this phase.

Never commit secrets, service-role keys, private documents, extraction output, or production data.

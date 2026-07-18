# TrustRAG

TrustRAG is a secure enterprise RAG platform for internal documents. It lets authenticated employees upload and query private knowledge while enforcing role- and department-based access **before retrieval and LLM generation**. Every answer is grounded in authorized source material, cited, audited, and refused when evidence is insufficient.

This repository intentionally contains planning and project-setup material only. It does not yet contain an application scaffold or runtime implementation.

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
apps/web/              Next.js frontend (future)
services/api/          FastAPI backend (future)
packages/              Shared contracts/configuration (future)
infra/                 Database, Supabase, and deployment configuration (future)
docs/                  Product and implementation context
```

Copy `.env.example` to `.env` when implementation begins. Never commit secrets, service-role keys, private documents, extraction output, or production data.

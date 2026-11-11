# Enterprise Intelligence RAG — Project and Interview Guide

Reviewed: 11 November 2026

## Project summary

Enterprise Intelligence RAG is a document question-answering workspace. A user signs in with a one-time email code, uploads a supported file, and asks questions answered from retrieved passages with citations.

The deployed demonstration uses Cloudflare Workers for the site and API, Cloudflare Access for email sign-in, D1 for workspace records and extracted text, Vectorize for embeddings, and Workers AI for embeddings and answer generation. A separate FastAPI/PostgreSQL/Qdrant implementation remains in the repository for local development and evaluation.

**The project is deployed for a controlled demonstration. It is not certified for confidential, regulated, or business-critical financial work.** The project owner reports successful email sign-in and answers. A read-only D1 count shows 1 user, 0 documents, 1 conversation, 2 messages, so document-grounded RAG has not yet been confirmed.

## Interview pitch

### 30-second explanation

“Enterprise Intelligence RAG lets a user ask questions across their own business documents and see which passages support each answer. The deployed app uses Cloudflare Access email one-time codes, a Cloudflare Worker API, D1 for persistent workspace data, Vectorize for semantic search, and Workers AI to draft concise cited answers. I added tenant isolation, input limits, citations, and a source-only fallback if generation is unavailable. I tested the frontend and Worker builds and the local backend test suite. I present it as a controlled demo: the owner confirmed sign-in and answers, while document-grounded retrieval, production security review, financial answer evaluation, and backup recovery still need validation.”

### Problem and solution

People often need to find a fact, date, risk, or figure across several business documents. This project extracts text, splits it into passages, indexes them, retrieves evidence for a question, and returns an answer with source references. It assists research; it does not make financial decisions or replace human review.

## Architecture and data flow

1. The browser opens the Worker-hosted site.
2. Cloudflare Access asks for the user’s email and sends a one-time PIN.
3. After sign-in, the browser sends workspace requests with its Access session.
4. The Worker verifies the Access assertion and uses the verified email to select the user’s D1 workspace.
5. The browser extracts text from the file and sends passages to the Worker.
6. The Worker saves extracted text and metadata in D1 and embeddings in Vectorize.
7. For a question, the Worker searches that user’s passages, optionally asks Workers AI to draft an answer, and returns citations.
8. The browser saves the question, answer, and citations in the user’s conversation history.

| Component | Responsibility |
|---|---|
| Next.js frontend | Workspace interface, browser-side file extraction, upload, chat, citations, document management |
| Cloudflare Access | Email one-time PIN sign-in and session gate |
| Cloudflare Worker | API, Access assertion validation, tenant selection, limits, retrieval, AI orchestration |
| Cloudflare D1 | User profiles, extracted text, metadata, conversations, messages, citations, daily AI counters |
| Cloudflare Vectorize | 384-dimensional vectors tagged with owner and document metadata |
| Cloudflare Workers AI | BGE Small embeddings and Llama 3.3 answer generation |

Live site: https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev

The Access policy allows any email address that can complete the email PIN flow. Session length is configured for 24 hours. Phone/SMS authentication is not configured.

## Authentication and user isolation

Cloudflare Access performs email verification. The Worker verifies the signed Access assertion, including issuer, signature, application audience, algorithm, and expiry. A caller cannot select another workspace by submitting a different email in an API request.

The verified email is normalized and mapped to a stable D1 user record. D1 reads and writes filter records by that user ID. Vectorize searches include an owner filter, and returned vector IDs are resolved through D1 rows belonging to the same owner before their text can be used as evidence.

Local tests exercise user isolation, but a live two-account browser test has not been completed. Firebase compatibility code remains in the repository. Cloudflare Access sign-in does not automatically import old Firestore-only records. The latest D1 count is 1 user, 0 documents, 1 conversation, 2 messages.

## Document ingestion

Supported file types are PDF, DOCX, TXT, and CSV. The browser extracts text with PDF.js, Mammoth, or built-in text reading. Original file bytes are not archived.

Text is split into passages of up to 2,000 characters. PDF page numbers are preserved when available. The browser sends passages, filename, size, content type, and labels to the Worker, which validates them before persistence.

Application limits:

- 5 MB per file
- 40,000 extracted characters per file
- 20 passages per document
- 50 documents and 1,000 passages per user
- 50 conversations per user
- 100 messages per conversation
- 6,000 characters per question

Scanned PDFs need OCR, which is not included. Deleting a document removes its D1 text and Vectorize vectors.

## Retrieval and answer generation

The Worker creates embeddings with Cloudflare’s BGE Small English model and stores them in Vectorize. For a question, it searches Vectorize for up to 30 passages filtered by owner, performs keyword search over that owner’s D1 passages, combines candidates, applies selected domain labels, and selects up to three passages.

The selected records become citations with document name, optional page number, and an excerpt. The Worker sends the question and cited excerpts to Llama 3.3 with instructions to use only supplied sources, ignore instructions inside source text, avoid personal financial advice, and report insufficient evidence. If generation is unavailable or the app budget is reached, the system can return source excerpts instead.

This is retrieval-augmented generation (RAG): retrieval supplies evidence before a language model drafts an answer. The model does not search the whole database by itself.

Daily AI limits are shared across all users of this app: 250,000 embedding input characters, 50,000 generation input characters, and 5,000 reserved output tokens. Cloudflare account-level plan and usage limits also apply; the deployment cannot guarantee a $0 bill in every account or usage scenario.

## Data model

| D1 record | Stored fields |
|---|---|
| users | Stable ID, verified email, legacy-import status, timestamps |
| documents | Owner, filename, content type, size, labels, timestamp, passage count |
| chunks | Owner, document, extracted text, vector ID, optional page number |
| conversations | Owner, title, timestamps |
| messages | Owner, conversation, role, content, citations, timestamp |
| daily_ai_usage | Per-day app-wide embedding and generation counters |

Original file bytes are not stored in D1 or an object bucket. Extracted text is kept to support later search; embeddings are kept in Vectorize. D1 is in Cloudflare’s APAC region. A read-only count check on 11 November 2026 returned 1 user, 0 documents, 1 conversation, 2 messages.

## Main Worker API routes

| Route | Purpose |
|---|---|
| GET /api/me | Return the verified workspace identity |
| GET or POST /api/documents | List documents or save extracted passages |
| DELETE /api/documents | Delete a document and its vectors |
| GET or POST /api/conversations | List or create conversations |
| GET or POST /api/conversations/{id}/messages | Read or save conversation messages |
| POST /api/answer | Retrieve evidence and draft a cited answer |
| GET /api/migrations/status | Read legacy-import status |
| POST /api/migrations/complete | Mark legacy import complete |
| GET /health/ready | Check D1 connectivity; this is also behind Access |

## Security and privacy choices

- Derive workspace identity from Cloudflare Access, not a client-supplied user ID.
- Filter D1 and Vectorize operations by owner and resolve vector results through owner-scoped D1 rows.
- Validate IDs, file metadata, passage sizes, question length, and JSON request sizes.
- Treat source passages as untrusted data in the answer prompt.
- Return citations so users can inspect the evidence.
- Keep the Cloudflare provisioning token in the ignored project-root .env. Never put it in frontend variables or commit it.
- Process original files in the browser and persist extracted text only.
- Apply document and AI usage limits.

These are risk-reduction measures, not a security certification. The project has not completed an independent threat model, regulated-data review, abuse/load test, backup/restore exercise, or formal financial-answer benchmark.

## Repository and alternate implementation

| Path | Contents |
|---|---|
| frontend/ | Next.js UI, browser file extraction, Cloudflare client, Firebase compatibility |
| cloudflare/rag-api/ | Deployed Worker, D1 migrations, Access verification, retrieval and AI |
| backend/ | Separate FastAPI service using PostgreSQL and Qdrant |
| docker-compose.yml | Local PostgreSQL, Qdrant, FastAPI, and frontend container configuration |
| docker-compose.cloud.yml | Separate paid-provider template with external secrets, images, volumes, and network |
| evaluation/ | Retrieval evaluation scripts and human-labelled benchmark format |
| docs/ | Deployment, free-tier, readiness, QA, and interview documentation |

The public deployment is the Cloudflare Worker. Docker is not required to open or use it. The FastAPI/PostgreSQL/Qdrant implementation is an alternate development/evaluation path. The current frontend workspace client calls the Cloudflare Worker, so the local compose file has not been verified as a complete standalone login-and-RAG experience. The separate cloud compose template needs actual image, database, Qdrant, secret, volume, and ingress values and is not part of the current Cloudflare deployment.

## Build and verification

The Cloudflare site is already deployed. For a rebuild, the documented scripts are:

- In frontend/: npm ci, npm run lint, npm run build:static
- In cloudflare/rag-api/: npm ci, npm run typecheck, npx wrangler deploy

The frontend build uses frontend/.env.local for its public Worker URL and auth mode. The root .env contains private provisioning settings and must stay out of Git.

Rechecked 11 November 2026:

- Frontend TypeScript check through npm run lint: passed.
- Next.js static build: passed.
- Cloudflare Worker TypeScript check and Wrangler deployment dry run: passed.
- Backend test suite: 16 passed, with one Starlette/httpx deprecation warning.
- Local Docker Compose configuration validation: passed.
- Live Worker redirects unauthenticated visitors to Cloudflare Access; the login page returned HTTP 200.
- Remote D1 counts: 1 user, 0 documents, 1 conversation, 2 messages.
- The project owner reports successful email sign-in and answers. Document upload/indexing, source citations, deletion, and live two-user isolation were not confirmed.
- Cloud Docker compose has required deployment values and was not deployed. Configuration validation is not a full container build or runtime test.

## Completion status

### Complete for a controlled demonstration

- Cloudflare website and API deployment
- Cloudflare Access email PIN policy
- D1 workspace persistence and migrations
- Vectorize embedding/search integration
- Workers AI answer generation, citations, and source-only fallback
- Owner-scoped access in code
- Application input and usage limits
- Frontend and Worker builds
- Backend unit tests
- GitHub source and documentation

### User acceptance still needed to verify document-grounded RAG

The owner reports that sign-in works and the app returns answers. The latest D1 count has 1 user, 1 conversation, 2 messages, and no documents, so it does not show that a source file has been indexed in this Cloudflare workspace.

1. Upload a small searchable PDF or TXT file, ask a question whose answer is in it, and inspect the citation.
2. Delete the test document and confirm it disappears.
3. For a multi-user check, sign in with a second email and verify it cannot see the first workspace.
4. Decide whether the allow-everyone sign-in policy suits the intended audience.

### Required before financial production use

Independent security/privacy review, a threat model, abuse controls and alerting, a human-reviewed retrieval and answer benchmark, tested backups/restores, provider retention/region review, account quota/cost monitoring, and any applicable financial, privacy, and data residency assessment.

## Interview questions

**Why RAG instead of fine-tuning?**
The app answers from current user documents. New documents can be indexed without retraining, and citations point back to the evidence.

**Why combine semantic and keyword search?**
Semantic search helps find related wording. Keyword search helps with exact names, dates, codes, and figures.

**How do you reduce unsupported answers?**
The model receives retrieved passages, is instructed to answer only from those sources, and is given citation markers. When evidence is missing it should say so; when generation is unavailable, the app can show source excerpts.

**How are users isolated?**
The Worker derives identity from a verified Access assertion. D1 queries filter by owner, Vectorize uses an owner metadata filter, and vector matches are resolved through owner-scoped D1 rows.

**Does the app keep uploaded documents?**
It keeps extracted text and metadata, not the original file bytes. The browser parses files before sending passages to the Worker.

**Is it ready for a bank or regulated financial use?**
No. It is a controlled demonstration. The owner reports successful sign-in and answers, but document-grounded use still needs validation; it also needs financial-answer evaluation, independent security/privacy review, backup/restore testing, and applicable compliance and residency reviews.

**What would you build next?**
Complete document-grounded answer and citation acceptance with two users, then add tested backups, abuse/rate controls, operational alerts, and a human-reviewed financial QA benchmark.

## Glossary

- **RAG:** Retrieve relevant source passages, then generate an answer using those passages.
- **Embedding:** A vector representation of text used to find semantically related passages.
- **Vector index:** A database optimized for similarity search over embeddings.
- **Citation:** A reference to the source passage used to support an answer.
- **Tenant isolation:** Rules that ensure each user can read only their own workspace records.
- **D1:** Cloudflare’s managed SQLite-compatible database for structured data.

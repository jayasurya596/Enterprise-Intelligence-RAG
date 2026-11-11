# Enterprise Intelligence RAG — Project Documentation

**Reviewed:** 11 November 2026
**Project type:** Cloudflare hosted document question-answering demonstration
**Live site:** [enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev](https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev)

## 1. Project overview

Enterprise Intelligence RAG is a web workspace for asking questions about a user's business documents. It extracts text from supported files, indexes passages, retrieves relevant evidence for a question, and returns an answer with source references when evidence is available.

The current hosted version uses Cloudflare Access for email one-time-code sign-in, a Cloudflare Worker for the API and static site, D1 for workspace records and extracted text, Vectorize for semantic search, and Workers AI for embeddings and answer generation. A separate FastAPI, PostgreSQL, and Qdrant implementation remains in the repository for local development and evaluation.

The service is available for a controlled demonstration. It is not certified or approved for confidential, regulated, or business-critical financial data. The project owner reports that sign-in works and the site returns answers. A read-only D1 count on 11 November 2026 showed 1 user, 0 documents, 1 conversation, and 2 messages. That confirms account and chat activity, but it does not confirm a document has been indexed or that an answer is grounded in uploaded material.

## 2. Goals and user flow

The intended user flow is:

1. Open the Worker site.
2. Enter an email address and complete Cloudflare Access's one-time PIN challenge.
3. Upload a supported PDF, DOCX, TXT, or CSV file.
4. Review the document in the workspace.
5. Ask a question about its contents.
6. Inspect the answer's citations and source excerpts.
7. Continue the conversation or delete the document.

The current Access policy allows anyone with an email inbox that can receive a PIN. Each verified identity gets an isolated workspace. Phone or SMS OTP is not configured. Original file bytes are parsed in the browser and are not archived; extracted text, metadata, and search vectors are stored by the backend services.

## 3. System architecture

```text
Browser
  ├─ Cloudflare Access email PIN and session
  ├─ Static Next.js workspace
  └─ Browser-side PDF/DOCX/TXT/CSV text extraction
         │ authenticated HTTPS requests
         ▼
Cloudflare Worker (static site + API)
  ├─ verifies Access assertion and derives workspace identity
  ├─ D1: users, documents, chunks, conversations, messages, usage
  ├─ Vectorize: owner-tagged text embeddings
  └─ Workers AI: BGE embeddings and Llama answer generation
```

| Component | Role in the hosted application |
|---|---|
| Next.js static frontend | Sign-in handoff, document and conversation interface, browser-side text extraction, chat, citations, and document management. |
| Cloudflare Access | Email one-time PIN identity check and session gate for the Worker hostname. |
| Cloudflare Worker | Serves the static site and API; validates Access assertions; applies limits; coordinates storage, retrieval, and generation. |
| Cloudflare D1 | Stores normalized user profiles, extracted passages, document metadata, conversations, messages, citations, and daily application AI counters. Database location is APAC. |
| Cloudflare Vectorize | Stores 384-dimensional embeddings and metadata used for similarity search, including owner and document identifiers. |
| Cloudflare Workers AI | Runs `@cf/baai/bge-small-en-v1.5` embeddings and `@cf/meta/llama-3.3-70b-instruct-fp8-fast` answer generation. |

The older Firebase Hosting and Firebase token compatibility code remains in the repository. It is not the currently documented Cloudflare sign-in path. Access sign-in does not automatically copy Firestore-only records into D1.

## 4. Authentication and workspace isolation

Cloudflare Access sends a one-time PIN to the email the user enters. The browser carries its Access session when calling the Worker. The Worker validates the signed Access assertion, including its signature, configured team issuer, application audience, algorithm, and expiry. Workspace identity comes from the validated assertion; a client-supplied user ID or email is not accepted as the authority for selecting another user's workspace.

The verified email is normalized and mapped to a stable D1 user ID. D1 queries and mutations are scoped to that ID. Vectorize queries add an `ownerUid` metadata filter. Vector matches are resolved against owner-scoped D1 rows before their text is included as evidence. Local tests exercise separate-user isolation, but a live two-email browser acceptance test has not been completed.

The Access application uses an allow-everyone policy and a 24-hour session. This is suitable only if open email-based registration is intended. For a private team, restrict the Access policy to named emails or an approved domain. Anyone controlling an email inbox can otherwise create a workspace. SMS authentication and account roles are not implemented.

## 5. Document ingestion and limits

The browser extracts text from PDF, DOCX, TXT, and CSV files. Scanned PDFs do not receive OCR. Text is split into passages (chunks); page information is retained where the extractor provides it. The Worker validates the file metadata and passages, stores extracted text in D1, and writes corresponding vectors to Vectorize. The original file is not retained in a bucket.

Configured application limits:

| Limit | Value |
|---|---:|
| File size | 5 MB per file |
| Extracted text | 40,000 characters per file |
| Passages | 20 per document; 1,000 per workspace |
| Documents | 50 per workspace |
| Conversations | 50 per workspace |
| Messages | 100 per conversation |
| Question length | 6,000 characters |
| Daily embedding input budget | 250,000 characters across this app |
| Daily generation input budget | 50,000 characters across this app |
| Daily reserved generation tokens | 5,000 across this app |

The application AI counters reset at 00:00 UTC. These application limits do not measure or guarantee Cloudflare account-wide usage or billing. When AI generation is unavailable or the application's budget is exhausted, the Worker can return retrieved source excerpts instead of a generated response. Indexing may be rejected after its app budget is reached.

Deleting a document is intended to remove its D1 records and Vectorize entries. Confirm this with a test upload before relying on deletion for sensitive information.

## 6. Retrieval and answer generation

The request path for an answer is:

1. Validate the Access identity and question input.
2. Create a query embedding with Workers AI when available.
3. Search Vectorize for up to 30 passages with a filter for the signed-in owner.
4. Run owner-scoped keyword retrieval over D1 so exact terms can contribute alongside semantic matches.
5. Combine and rank candidates, apply the supported domain filters, and select up to three passages as context.
6. Ask the answer model to use only the supplied excerpts, ignore instructions embedded in source material, avoid personalized financial advice, and acknowledge missing evidence.
7. Return the answer and citation metadata (document name, optional page number, and excerpt). If generation is unavailable, return source excerpts when possible.
8. Save the user question, assistant response, and citations in the conversation history.

This is retrieval-augmented generation (RAG): the model receives selected evidence retrieved for the current question. It does not perform a general search across every document itself. Citations help a user inspect supporting passages, but they do not prove the model interpreted the passage correctly. Financial facts and recommendations require human review.

## 7. Data model and retention

| Record | Purpose | Stored in |
|---|---|---|
| User profile | Stable workspace ID, normalized verified email, legacy status, timestamps | D1 |
| Document | Owner, filename, content type, size, labels, timestamps, passage count | D1 |
| Chunk | Extracted passage, owner/document IDs, optional page, vector ID | D1 |
| Embedding | Search vector and owner/document/chunk metadata | Vectorize |
| Conversation | Owner, title, timestamps | D1 |
| Message | Owner, conversation, role, content, citations, timestamp | D1 |
| AI usage counter | App-wide daily embedding and generation accounting | D1 |

Original PDFs, Word files, and other uploaded bytes are not archived. Extracted text remains stored to support search and later use. Questions and answers are also stored in conversation history. Review Cloudflare's current service terms, retention, access controls, account region, and any relevant data-handling requirements before uploading personal or confidential information.

## 8. API surface

The Worker currently handles these application routes. Cloudflare Access protects the Worker hostname, including the site and API.

| Method and route | Purpose |
|---|---|
| `GET /api/me` | Return the verified workspace identity/profile. |
| `GET /api/documents` | List the signed-in user's documents. |
| `POST /api/documents` | Validate and persist extracted passages and their embeddings. |
| `DELETE /api/documents` | Remove a document and associated searchable records. |
| `GET /api/conversations` | List the user's conversations. |
| `POST /api/conversations` | Create a conversation. |
| `GET /api/conversations/{id}/messages` | Read messages for an owner-scoped conversation. |
| `POST /api/conversations/{id}/messages` | Save a message for an owner-scoped conversation. |
| `POST /api/answer` | Retrieve evidence and produce an answer with source metadata when available. |
| `GET /api/migrations/status` | Read legacy-import status. |
| `POST /api/migrations/complete` | Mark a legacy-import flow complete. |
| `GET /health/ready` | Check D1 readiness; the endpoint is behind Access on the live hostname. |

## 9. Repository map

| Path | Contents |
|---|---|
| `frontend/` | Next.js UI, static build setup, browser-side file extraction, Cloudflare client, and Firebase compatibility. |
| `cloudflare/rag-api/` | Deployed Worker code, Wrangler configuration, D1 migrations, Access verification, retrieval, and AI orchestration. |
| `backend/` | Separate FastAPI service, PostgreSQL persistence, Qdrant integration, migrations, and tests for local development/evaluation. |
| `docker-compose.yml` | Local PostgreSQL, Qdrant, FastAPI, and frontend container configuration. |
| `docker-compose.cloud.yml` | Separate external/cloud container template requiring provider-specific images, credentials, storage, and ingress values. It is not the active Cloudflare deployment. |
| `evaluation/` | Retrieval evaluation utilities and benchmark format. |
| `docs/` | Deployment, QA, cost, readiness, project, and interview documentation. |

The public Cloudflare app does not depend on Docker. The local compose stack and the separate cloud compose template are alternate paths; the cloud template was not deployed, and the local compose file was not verified as a complete standalone Cloudflare-login and RAG experience.

## 10. Local development and deployment

### Prerequisites

- Node.js and npm versions compatible with the lockfiles.
- Python version compatible with `backend/requirements.txt` for the local backend.
- Docker Desktop only when using the local compose stack.
- Cloudflare account access and Wrangler authentication only when deploying the Cloudflare Worker.

### Configure the frontend

Set these public build-time values in `frontend/.env.local`:

```text
NEXT_PUBLIC_AUTH_MODE=cloudflare-access
NEXT_PUBLIC_CLOUDFLARE_API_URL=https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev
```

The project-root `.env` contains local provisioning settings and a private Cloudflare API token. It is ignored by Git. Do not copy secrets into frontend variables, Docker build arguments, screenshots, or GitHub. The deployed Worker does not need the provisioning token at runtime.

### Build and deploy the Cloudflare path

From the repository root:

```text
cd frontend
npm ci
npm run lint
npm run build:static

cd ../cloudflare/rag-api
npm ci
npm run typecheck
npx wrangler deploy
```

The configured Access team domain and audience must match the Cloudflare Access application. If that application is recreated, its audience can change; update the Worker configuration and redeploy. Apply future D1 schema migrations with:

```text
npx wrangler d1 migrations apply enterprise-intelligence-rag --remote
```

The live site and API share the Worker URL. Unauthenticated requests are redirected to Cloudflare Access, so `/health/ready` is not a public health endpoint.

### Local backend path

`docker-compose.yml` starts the alternate FastAPI/PostgreSQL/Qdrant stack. Use the environment template and compose file for local variables; never commit the real `.env`. This path is separate from the hosted Cloudflare Worker and does not change the live deployment.

## 11. Verification and current status

Checks rerun on 11 November 2026:

- Frontend TypeScript check (`npm run lint`): passed.
- Next.js static production build (`npm run build:static`): passed.
- Cloudflare Worker TypeScript check: passed.
- Wrangler deployment dry run: passed and recognized D1, Vectorize, Workers AI, static assets, and Access configuration.
- Backend test suite: 16 passed; one Starlette/httpx deprecation warning.
- Local `docker-compose.yml` configuration parsing: passed.
- Live unauthenticated Worker request: redirected to Cloudflare Access; the Access sign-in page returned HTTP 200 in the check.
- Remote D1 aggregate counts: 1 user, 0 documents, 1 conversation, 2 messages.
- The Cloudflare Worker had not changed since the deployed version recorded in the QA report; the changes in this handoff are documentation only.

The owner reports being able to sign in and receive answers. Since the live D1 count contains no documents or chunks, these acceptance items remain open:

1. Upload a small PDF or TXT file and confirm it appears in the workspace.
2. Ask a question with a known answer in that file and verify the citation and excerpt.
3. Delete the test document and confirm it disappears from the workspace and no longer appears in search.
4. Sign in with a second email and confirm it cannot see the first account's documents or conversations.

The cloud compose template requires actual image references, database/Qdrant credentials, storage, and ingress values and was not deployed. Build/test success does not equal full live acceptance or financial-production readiness.

## 12. Risks and known limitations

- Any email address can register through the current Access policy; restrict it before using the app with a closed group.
- There is no SMS OTP, organization role model, or administrator console.
- No OCR is included for scanned PDFs.
- Original file bytes are not retained, but extracted document text and chat history are persisted.
- Old Firestore-only records are not automatically imported by Cloudflare Access sign-in.
- The owner-scoped behavior has local test evidence, but live multi-user isolation still needs acceptance.
- The latest live database counts do not establish successful upload, indexing, citation, or document deletion.
- No independent security review, threat model, formal privacy/compliance assessment, financial-answer benchmark, load/abuse test, or backup/restore exercise has been completed.
- Cloudflare free allowances are finite and vary by account and service. The app cannot promise a $0 bill under all account settings or use. Check account billing and service dashboards.
- The app is a research assistant demonstration, not financial advice or an automated financial decision system.

## 13. Glossary

- **RAG:** Retrieval-augmented generation; retrieve relevant source passages, then generate an answer using those passages.
- **Embedding:** A numeric representation of text used to find semantically similar content.
- **Vectorize:** Cloudflare's vector-search service used by this project to find similar passages.
- **Chunk/passage:** A bounded section of extracted document text indexed for retrieval.
- **Citation:** Metadata and an excerpt that point the user to retrieved supporting text.
- **Tenant/workspace isolation:** Scoping records and searches so one user cannot access another user's data.
- **D1:** Cloudflare's managed SQLite-compatible database used for structured workspace data.
- **Access assertion:** A signed identity statement issued by Cloudflare Access and verified by the Worker.

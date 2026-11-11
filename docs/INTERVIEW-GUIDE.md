# Enterprise Intelligence RAG — Interview Guide

**Last reviewed:** 11 November 2026

## 1. One-line description

An email-authenticated document question-answering web app that retrieves passages from a user's files and uses them to produce answers with inspectable citations.

## 2. 30-second pitch

> “I built Enterprise Intelligence RAG, a document question-answering workspace. A user signs in with a Cloudflare Access email one-time code, uploads a supported file, and asks questions against its extracted text. The hosted architecture uses a Cloudflare Worker API, D1 for workspace and chat data, Vectorize for semantic retrieval, and Workers AI for embeddings and answer generation. I designed the API to derive identity from a verified Access assertion and scope both database and vector searches by user. The frontend and Worker builds pass, and the separate backend suite has 16 passing tests. I describe it as a controlled demo: document-grounded live acceptance, independent security review, backups, and financial answer evaluation are still pending.”

## 3. Two-minute explanation

> “The problem I focused on is that people need to find specific facts across multiple documents and want to see the evidence behind an answer. Enterprise Intelligence RAG parses PDF, DOCX, TXT, and CSV text in the browser, divides it into passages, stores the extracted passages in D1, and stores their embeddings in Vectorize. When a user asks a question, the Worker validates the Cloudflare Access identity, searches only that user's vector and keyword results, chooses a small set of relevant passages, and sends those excerpts to Workers AI. The response includes source details so the user can inspect the evidence. If generation is unavailable, the service can return source passages instead.
>
> “The hosted site and API share a Cloudflare Worker. Cloudflare Access handles email one-time PIN login. The Worker derives the workspace from the signed assertion rather than trusting an ID supplied by the browser. D1 stores accounts, document text and metadata, chats, messages, and citations; Vectorize stores owner-tagged vectors. The source also contains a separate FastAPI, PostgreSQL, and Qdrant implementation for local development and evaluation.
>
> “I added input and usage limits and prompts that treat retrieved documents as untrusted source material. The static frontend and Worker checks pass, and the backend tests pass. I’m careful about the current scope: the owner reports successful login and answers, but the latest live D1 count had no document rows. So I still need to complete a live upload, citation, deletion, and second-user isolation acceptance test before calling document-grounded behavior fully verified. I would not use this demo with sensitive financial data until security, privacy, backup, and answer-quality reviews are complete.”

## 4. Architecture to sketch on a whiteboard

```text
User browser
   │ email PIN / Access session
   ▼
Cloudflare Access ── protects site and API
   │ signed identity assertion
   ▼
Cloudflare Worker API
   ├── D1: users, documents, chunks, conversations, messages
   ├── Vectorize: owner-filtered semantic search
   └── Workers AI: embeddings + answer drafting
           ▲
   citations and answer
```

Describe the request path in this order: authenticate; derive the workspace from the verified identity; retrieve owner-scoped evidence; generate from selected passages; return and persist the answer with citations.

## 5. Demo script (about five minutes)

Use a small, non-sensitive sample file with a few clear facts. Do not use a real customer, investor, or employer document.

1. Open the live site and complete the email one-time PIN flow.
2. Show the empty or existing workspace and explain the account is protected by Cloudflare Access.
3. Upload the sample TXT or text-based PDF and wait for indexing to complete.
4. Ask a question whose answer appears plainly in the sample.
5. Open the citation or source excerpt and show how it supports the answer.
6. Ask a question that the sample does not answer and show the expected abstention/source-only behavior.
7. Delete the sample document and verify it is removed.
8. Explain that two-account isolation is enforced in code and locally tested; only claim a live check if you personally complete it during the demo.

If upload or citations do not work during the live demo, do not present a canned answer as if it came from a live document. Show the architecture and test evidence, then say the live document-grounding acceptance check remains open.

## 6. Likely questions and concise answers

### Why use RAG instead of fine-tuning?

The target information is in changing user documents. RAG can index new files without retraining and can return the passages used to support an answer. Fine-tuning is not a substitute for retrieving current source facts.

### Why use both semantic and keyword retrieval?

Semantic search can find related wording. Keyword search can help with exact names, dates, identifiers, and numbers. Combining them gives the system two ways to surface useful evidence.

### How does user isolation work?

Cloudflare Access issues a signed assertion. The Worker verifies it and uses the verified identity to map the request to a D1 user ID. D1 queries are owner-scoped, Vectorize searches include an owner filter, and vector results are resolved through owner-scoped D1 records. Local tests cover a second simulated identity. A live second-account browser acceptance check is still pending.

### What happens to an uploaded file?

The browser extracts text from PDF, DOCX, TXT, or CSV. The original file bytes are not archived. Extracted text and metadata are stored in D1, and embeddings are stored in Vectorize. Chat questions and answers are also persisted.

### How do you reduce hallucinations or prompt injection?

The Worker sends selected excerpts and asks the model to answer only from them, ignore instructions found inside source documents, and report when evidence is insufficient. It returns citations for inspection, and has a source-excerpt fallback. These measures reduce risk but do not guarantee factual correctness.

### What is the current completion status?

The Worker is deployed behind Cloudflare Access. Frontend and Worker builds pass, and 16 backend tests pass. The owner reports successful email sign-in and answers. However, the latest live D1 check showed 1 user, 0 documents, 1 conversation, and 2 messages, so I have not verified a live document-grounded answer, citation, deletion, or two-account flow. It is a controlled demo, not production-ready financial software.

### Why is there a FastAPI/PostgreSQL/Qdrant backend if the app uses Cloudflare?

It is an alternate local development/evaluation implementation kept in the repository. The current public website calls the Cloudflare Worker and uses D1, Vectorize, and Workers AI. The two deployment paths should not be confused.

### How do you handle cost?

The design uses Cloudflare's included/free allowances where available and applies app-level daily AI limits. The account's usage can include other services, and included quotas or plan terms can change. I therefore describe the deployment as free-tier-oriented, not a guaranteed zero-cost service.

### What would you improve next?

First complete and document live upload, retrieval, citation, deletion, and two-user acceptance. Then add monitored backups and restore drills, rate/abuse monitoring, restricted access if required, a human-reviewed financial QA benchmark, and an independent security/privacy review.

### Is it suitable for a bank or for making financial decisions?

No. It is a demonstration research assistant. It lacks a formal financial answer benchmark, independent security and privacy review, compliance assessment, backup/restore evidence, and production operations. Responses need human verification.

## 7. Honest evidence to mention

**Verified in the latest project recheck:**

- Frontend TypeScript check and static production build passed.
- Cloudflare Worker typecheck and Wrangler dry run passed.
- Backend pytest suite: 16 passed, with one deprecation warning.
- Local Docker Compose configuration parsed successfully.
- Live unauthenticated requests redirect to Cloudflare Access; the Access page returned HTTP 200 in the check.
- The project owner reports signing in and getting answers.

**Still needs live acceptance:**

- Upload and index a document in the Cloudflare workspace.
- Confirm an answer cites the expected passage.
- Delete the document and confirm it is no longer searchable.
- Use two email accounts to validate live workspace isolation.
- Complete an independent security/privacy, backup/restore, and financial-answer quality review before production use.

## 8. Terms to know

- **RAG:** Retrieve relevant document passages, then generate an answer using those passages.
- **Embedding:** A vector representation of text that supports similarity search.
- **Chunk:** A short passage created from a document for indexing and retrieval.
- **Vector search:** Similarity-based search over embeddings.
- **Citation:** A reference and excerpt that let the user inspect retrieved support.
- **Tenant isolation:** Ensuring each account can access only its own workspace.
- **Abstention:** Saying the available evidence is insufficient instead of guessing.

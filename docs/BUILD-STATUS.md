# Build, QA, and deployment status

Updated: 2026-11-11

## Live deployment

- Website and API: [https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev](https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev)
- Cloudflare Access team domain: floral-waterfall-2ff2.cloudflareaccess.com
- Cloudflare D1 database: enterprise-intelligence-rag, APAC
- Vectorize index: enterprise-intelligence-rag-vectors, 384 dimensions, cosine metric, ownerUid metadata filter
- Worker version: bdbfd96f-37b1-4a30-884f-ed290097afd0

Cloudflare Access protects the full Worker hostname. An unauthenticated browser gets HTTP 302 to the Access login page. The Access page responds HTTP 200. The API's unauthenticated /api/me request is also redirected to email sign-in. After a signed-in request, the Worker verifies the Access assertion using the configured team issuer and app audience.

Cloudflare Access is restricted to the One-time PIN identity provider. The policy allows every email address, and the app uses a 24-hour session. This supports a public demo where each person signs in to their own workspace.

## Implemented architecture

- Cloudflare Access handles email one-time PIN authentication for the hosted site; there is no app password or SMS flow.
- The Worker verifies Access JWT signature, issuer, audience, algorithm, and expiry. It uses the verified email to create a D1 user row and owner-scoped workspace.
- When a matching email already has a D1 user profile from the legacy Firebase token path, the Worker reuses that owner ID.
- D1 stores profiles, extracted text chunks, document metadata, conversations, messages, citations, and daily AI counters.
- Vectorize stores embeddings; queries include an owner UID filter and returned chunks are checked against that owner.
- Workers AI uses BGE Small embeddings and Llama 3.3 70B FP8 Fast. If AI inference or the app budget is unavailable, the API falls back to source excerpts/keyword retrieval.
- File parsing remains in the browser. Extracted text goes to Cloudflare; original files are not archived.
- The older Firebase Hosting copy and legacy Firebase-token verification remain in the repository for compatibility, but they are not the current hosted login flow.
- Old Firestore-only content is not automatically imported by Access sign-in. D1 was empty at initial deployment; the later 2026-11-11 count was 1 user, 0 documents, 1 conversation, 2 messages.

## Application limits

- 5 MB maximum file
- 40,000 extracted characters per file
- 20 chunks per document
- 50 documents and 1,000 chunks per account
- 50 conversations per account
- 100 messages per conversation
- Daily app AI budget: 250,000 embedding input characters, 50,000 generation input characters, and 5,000 reserved output tokens; resets at 00:00 UTC

The AI budget applies to this app only and cannot see requests from other Workers on the Cloudflare account. Workers AI provides a finite included allowance; usage beyond plan limits can be billable. Monitor the account-level usage dashboard.

## QA performed

- Frontend npm run lint: passed.
- Frontend npm run build:static: passed in Cloudflare Access mode.
- Cloudflare Worker npm run typecheck: passed.
- Wrangler deployment dry run: passed and confirmed D1, Vectorize, Workers AI, and Access verifier bindings/variables.
- Worker deployment: succeeded; current version bdbfd96f-37b1-4a30-884f-ed290097afd0.
- Local readiness and static homepage before Access activation: HTTP 200.
- Local API without a valid identity: HTTP 401; allowed CORS preflight HTTP 204; blocked origin HTTP 403.
- Local simulated Access identity: /api/me HTTP 200; D1 profile creation succeeded; conversation and message writes/read succeeded; second simulated email saw no first-user conversation.
- Local malformed Access assertion: HTTP 401.
- Live unauthenticated homepage: HTTP 302 to the Cloudflare Access email login.
- Live Access login page: HTTP 200; email and code-related text present.
- Live unauthenticated /api/me: HTTP 302 to Access login.
- Access application check: self-hosted app on the Worker hostname, one-time PIN provider only, allow-everyone policy.
- Current D1 aggregate counts on 2026-11-11: 1 user, 0 documents, 1 conversation, 2 messages.
- Existing Cloudflare Access app for Telecom Churn was not modified.

## Live user acceptance and remaining checks

The project owner reports successfully signing in with email and receiving answers from the live app. The latest read-only D1 count shows 1 user, 0 documents, 1 conversation, 2 messages. This confirms workspace/chat activity but does not confirm document ingestion or a source-grounded answer. Upload a small TXT/PDF, verify its citation, delete it, and test a second account for isolation. Do not share email PINs in chat.

The Cloudflare app is available for a controlled demonstration. It is not certified for confidential or business-critical financial workloads. Security review, abuse/load testing, financial-answer benchmarking, backups, and restore exercises remain incomplete.


## Recheck on 11 November 2026

- Frontend TypeScript check and static production build: passed.
- Cloudflare Worker typecheck and Wrangler dry run: passed.
- Backend pytest suite: 16 passed; one Starlette/httpx deprecation warning.
- Local Docker Compose configuration parsed successfully. The separate cloud compose template requires actual image, database, Qdrant, secret, volume, and ingress values and was not deployed.
- The live Worker redirected an unauthenticated request to Cloudflare Access; the email sign-in page returned HTTP 200.
- A read-only query of remote D1 returned 1 user, 0 documents, 1 conversation, 2 messages.
- The project owner reports that email sign-in succeeds and the app returns answers. Since D1 has no document rows, document-grounded retrieval/citation and delete acceptance remain unverified.

**Readiness decision:** the Cloudflare application is deployed for a controlled demo and its owner reports successful sign-in and answers. A document upload/search/citation/delete check and live two-user isolation check remain. The app is not certified for production financial data.
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
- Old Firestore-only content is not imported by Access sign-in. The remote D1 database had 0 users, documents, and conversations when checked on 2026-11-11.

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
- D1 remote counts on 2026-11-11: 0 users, 0 documents, 0 conversations.
- Existing Cloudflare Access app for Telecom Churn was not modified.

## Still needs a real user check

A real email address and mailbox OTP were not used, so actual code delivery and sign-in have not been proven. After you sign in with your own email code, verify that the workspace opens and that a document can be uploaded, searched, and deleted. Do not send the OTP code in chat.

This is ready for a controlled demonstration after the real inbox acceptance check. It is not ready for confidential or business-critical financial workloads. Security certification, abuse/load testing, financial-answer benchmarking, backups, and restore exercises remain incomplete.

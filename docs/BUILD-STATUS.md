# Build, QA, and deployment status

Updated: 2026-11-09

## Live deployment

- Website and Cloudflare Worker API: [https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev](https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev)
- Previous Firebase Hosting address (fallback): [https://eirag-rag-261106-a7c9.web.app](https://eirag-rag-261106-a7c9.web.app)
- Worker readiness route: /health/ready
- Cloudflare D1 database: enterprise-intelligence-rag, provisioned in APAC
- Vectorize index: enterprise-intelligence-rag-vectors, 384 dimensions, cosine metric, ownerUid metadata filter
- Firebase project: eirag-rag-261106-a7c9

The static site and API are published together on the Cloudflare Worker. The homepage and JavaScript assets returned HTTP 200, the readiness endpoint returned HTTP 200, and the API rejected an unauthenticated workspace request with HTTP 401. D1 migrations 0001_init.sql, 0002_daily_ai_budget.sql, and 0003_tenant_scoped_ids.sql are applied remotely. The latest migration lets the legacy Firestore document, conversation, and message slot IDs safely repeat across accounts and conversations.

## Implemented architecture

- Firebase Authentication owns account credentials and email/password login. A verified email link is required before workspace access.
- The Worker verifies Firebase ID tokens, including signature, issuer, audience, expiry, UID, and email_verified claim.
- Cloudflare D1 stores the verified UID/email profile and owner-scoped documents, text chunks, conversations, messages, citations, and daily AI usage counters.
- Cloudflare Vectorize stores document embeddings. Queries include the authenticated UID filter, and returned chunk records are fetched from D1 with that same UID.
- Workers AI uses BGE Small for embeddings and Llama 3.3 70B FP8 Fast for grounded answer drafts. Both model endpoints returned HTTP 200 in a small non-sensitive smoke request. When AI inference is unavailable or the app's daily budget is exhausted, the API falls back to source excerpts/keyword retrieval.
- File parsing remains in the browser. Extracted text goes to Cloudflare; original files are not archived.
- On first verified login after this upgrade, existing Firestore documents, chats, and messages are copied to Cloudflare. Existing Firestore records are not deleted.

Firebase remains the identity provider and legacy Firestore migration source. Passwords are not copied to D1 or exposed to the Worker.

## Application limits

- 5 MB maximum file
- 40,000 extracted characters per file
- 20 chunks per document
- 50 documents and 1,000 chunks per account
- 50 conversations per account
- 100 messages per conversation
- Daily app AI budget: 250,000 embedding input characters, 50,000 generation input characters, and 5,000 reserved output tokens; resets at 00:00 UTC

The AI budget applies to this app only and cannot see requests from other Workers on the Cloudflare account. Cloudflare Workers AI provides 10,000 neurons per account/day without charge; Workers Paid usage above that is billable. Monitor the account-wide dashboard. [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/).

## QA performed

- Frontend npm run lint: passed.
- Frontend npm run build:static: passed with the deployment environment configured.
- Cloudflare Worker npm run typecheck: passed.
- Wrangler deployment dry run: passed and showed the D1, Vectorize, and AI bindings.
- Wrangler static asset dry run: passed and confirmed the generated frontend assets are included with the Worker.
- Cloudflare Worker deployment: completed; readiness endpoint returned HTTP 200.
- Cloudflare website homepage and JavaScript assets: HTTP 200; single-page fallback route: HTTP 200.
- API request without a bearer token: HTTP 401.
- Disallowed browser origin: HTTP 403.
- Approved website preflight: HTTP 204.
- D1 remote migrations: all three applied; tenant-scoped keys were verified by inserting duplicate document/conversation/message slot IDs under separate owners and duplicate message slots in separate conversations. Temporary test rows were deleted afterward.
- Vectorize index and ownerUid metadata index: present.
- Firebase Hosting fallback: retained; Cloudflare is now the primary site and API.
- Docker web image: compose config validation and build passed; web container was recreated with Firebase and Cloudflare build settings.

## Not verified

- No actual account signup or email delivery was initiated as part of this change.
- No signed-in end-to-end upload, D1 write/read, Vectorize query, generated answer, conversation persistence, or legacy Firestore migration was exercised with a real verified user's token.
- Numeric email OTP and phone SMS OTP are not implemented.
- No production security certification, abuse/load exercise, financial RAG benchmark, retention review, backup/restore drill, or incident response process was completed.

The deployed site is ready for a controlled demonstration and signed-in acceptance check. Do not treat it as ready for confidential or business-critical financial workloads.

# Financial RAG readiness review

## Current decision

The website and Cloudflare backend are deployed for a controlled demonstration:

- Website and API: [https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev](https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev)
- Firebase Hosting fallback: [https://eirag-rag-261106-a7c9.web.app](https://eirag-rag-261106-a7c9.web.app)

This is **not production-ready for confidential or business-critical financial data**.

## Requirement status

| Requirement | Status | Notes |
|---|---|---|
| Public site | Deployed | Cloudflare Worker serves the static frontend and API from one address. |
| Persistent accounts | Implemented, signup unverified | Firebase Authentication owns email/password credentials. |
| Email ownership | Implemented in source | Real verification link; delivery was not exercised during this change. |
| Numeric email OTP | Not implemented | Deployed flow is a link, not a numeric code. |
| Phone OTP | Not implemented | No SMS provider or real-number test is configured. |
| Cloud workspace storage | Deployed | D1 stores profile UID/email, document text, chats, and citations. |
| Semantic retrieval | Deployed in code | Vectorize and owner metadata filter are present; authenticated query was not exercised. |
| Generative answers | Deployed in code | Workers AI binding is present; authenticated answer generation was not exercised. |
| Tenant isolation | Implemented in code | Token verification plus owner-scoped D1 queries and Vectorize filter; needs full signed-in test. |
| Legacy data migration | Implemented in code | First verified login copies Firestore content; source records are preserved. |
| Free usage | Limited | App AI budget is not account-wide; paid overage can still occur from other account usage. |
| Financial accuracy/compliance | Not passing | No human-labeled benchmark, legal/regulatory assessment, or certification. |

## QA evidence and remaining gaps

The frontend typecheck and Firebase static build pass. The Worker typecheck and Wrangler dry run pass. The deployed Worker returned HTTP 200 from readiness, HTTP 401 without a token, HTTP 403 to a disallowed origin, and HTTP 204 for the approved-site preflight. All three D1 migrations are applied, including tenant-scoped IDs; a temporary remote SQL check confirmed that identical legacy IDs can exist across accounts and conversations. The temporary rows were deleted. Vectorize has the owner metadata index. A small model smoke request confirmed that both embedding and answer-generation models are callable.

A verified Firebase account is still needed for end-to-end tests of sign-in, first-run Firestore migration, document indexing, cross-account isolation, search, answer generation, deletion, and message persistence. No real registration email or OTP was sent in this change.

## Required before production use

- Complete a signed-in test with two verified accounts and confirm they cannot see each other's records.
- Implement numeric email OTP and real SMS OTP with a provider, budget, rate limits, and abuse protections if those are mandatory.
- Conduct a threat model and independent security review, including prompt injection, upload parsing, token abuse, and account recovery.
- Define organization roles, administrator workflows, support procedures, and global quotas/rate limits.
- Review provider data-processing terms, retention/deletion, APAC location, and financial-data residency obligations.
- Build a human-reviewed financial retrieval/answer benchmark and define when the system must abstain.
- Add monitored backups, restore testing, alerts, and incident response.
- Confirm Cloudflare plan and account-wide AI use against the desired spend target.

Do not market this build as a compliant financial decision system or upload sensitive investor/customer records before those reviews.

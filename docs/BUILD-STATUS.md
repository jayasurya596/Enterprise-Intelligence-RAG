# Build, QA, and deployment status

## Current target

- Domain: financial
- Spend target: strict $0; project billing is not enabled and no billing account is attached
- Deployment: Firebase Hosting on the no-cost Spark plan
- Approach: upgrade the existing project
- Firestore location: `asia-south1` (Mumbai)
- Live demo: [https://eirag-rag-261106-a7c9.web.app](https://eirag-rag-261106-a7c9.web.app)
- Firebase project: `eirag-rag-261106-a7c9` (`Enterprise RAG Free Demo`)

## Deployed resources

- Firebase web app `1:381582891215:web:7ddf7b6d492beb33813fba`.
- Firebase Authentication with email/password enabled. The application requires a verified email link before workspace access.
- Standard Native Firestore `(default)` database in `asia-south1`, with the free-tier flag enabled.
- Firestore rules compiled and published to the `cloud.firestore` release.
- Firebase Hosting version finalized and serving the static site.
- Billing status checked: no billing account is attached; no billing link was created.

## Changes delivered

- Added a static Firebase web application with email/password authentication and mandatory email verification before workspace access.
- Added Firestore prototype rules for verified-owner access, field validation, fixed-slot workspace caps, and client-side storage for extracted document text, metadata, chat history, and citations.
- Added in-browser PDF, DOCX, TXT, and CSV text extraction, lexical matching, and source excerpts.
- Added limits of 5 MB/file, 40,000 extracted characters/file, 20 chunks/file, 50 documents/account, 1,000 chunks/account, 50 conversations/account, and 100 messages/conversation.
- Kept the original Docker/FastAPI/PostgreSQL/Qdrant project for local development; it is not part of the hosted Firebase site.

## QA checks run on 2026-11-08

- Frontend TypeScript check (`npm run lint`): passed.
- Frontend dependency audit (`npm audit --omit=dev --audit-level=high`): zero vulnerabilities reported.
- Firebase static production build using the project's web configuration: passed.
- Backend test suite: 16 passed. One Starlette deprecation warning remains for the test client using httpx.
- Firebase JSON configuration and project alias parsed successfully.
- Firebase Rules API compiler: passed; deployed `cloud.firestore` rules release is active.
- Five simulated Firebase Rules allow/deny read cases passed: verified owner, unverified user, other owner, anonymous user, and out-of-range document slot. These were simulated rule checks, not writes or emulator tests.
- Live Hosting request returned HTTP 200. Browser smoke check confirmed the sign-in and create-account screens render.
- `npm audit` reported no high-severity production dependency vulnerabilities.

## Not verified or not implemented

- No account registration was submitted, so no real verification email was sent and mailbox delivery was not tested.
- No authenticated live Firestore write/read was exercised by a real user account.
- The Firestore emulator suite was not run because Java is unavailable. Docker Compose was not checked because Docker CLI was not available on PATH during QA.
- Numeric email OTP and real phone SMS OTP are excluded from the strict-$0 setup. Email verification is by link.
- No confidential financial documents were uploaded.
- No formal financial quality, security, abuse, load, backup/restore, residency, or compliance review has been completed.
- Fixed Firestore document IDs cap each account at 50 documents, 20 chunks/document, 50 conversations, and 100 messages/conversation. There is no global rate limit across accounts, so shared Spark quotas remain vulnerable to aggregate usage.
- The deployed app is a lightweight lexical retrieval demo, not semantic or generative RAG. The separate local Docker/FastAPI application is not deployed.

## Security rule audit

Static review score: **4/5 (strong prototype controls; not production certification)**. Rules use email-verified ownership from the authenticated UID path, explicit schemas and bounds, one-way document status changes, immutable child records, and default-deny behavior. Firebase's rules compiler accepted the deployed rules, and five simulated read allow/deny cases passed. Remaining findings are project-wide abuse limits, possible orphan child chunks if an owner deletes metadata directly, and lack of broader emulator write-path testing. See [FIRESTORE-RULES-AUDIT.json](FIRESTORE-RULES-AUDIT.json). Do not broadly share the app based only on this static review.

## User-facing limits

Email verification uses a real link, not an OTP code. Search is word-overlap ranking and quoted source excerpts, not generative AI. Extracted text and conversation data go to Firestore when a signed-in user uses the site; original files are not archived. Firebase's free quotas are limited and service may pause if quotas are exhausted. This prototype is not production-ready for confidential or business-critical financial records.

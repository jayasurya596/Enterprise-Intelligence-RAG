# Enterprise Intelligence RAG

## Current build

This project now includes a strict-$0 Firebase prototype alongside the original local Docker RAG stack. The cloud prototype is a static Next.js site intended for Firebase Hosting, with Firebase Authentication and Cloud Firestore. It does not need a paid model API or an always-on backend.

**Deployment status:** the strict-$0 demo is live at [https://eirag-rag-261106-a7c9.web.app](https://eirag-rag-261106-a7c9.web.app). Firebase Authentication uses email/password with an email verification link; Firestore stores account-owned workspace data, and Hosting serves the static site. The project has no billing account attached. This is an investor demo, not a production financial service. See [docs/BUILD-STATUS.md](docs/BUILD-STATUS.md).

## What the free prototype does

- Creates email/password accounts using Firebase Authentication and requires email verification by link.
- Saves account-owned document text, conversation messages, and citations in Cloud Firestore.
- Extracts text in the browser from PDF, DOCX, TXT, and CSV files up to 5 MB each.
- Searches extracted text by lexical word overlap and returns source excerpts. It does not call a generative model.
- Keeps original uploaded files in the browser only; it does not archive the originals.
- Enforces 50 documents, 20 chunks per document (1,000 total), 50 conversations, and 100 messages per conversation with fixed Firestore ID slots and matching rules.

The $0 profile has no numeric email OTP and no real phone SMS OTP. Firebase's email verification is a link, not a numeric code. The public prototype is not certified for production financial data. Firestore and Hosting also have account/project quotas; service can be limited when those quotas are reached. See [Firebase Authentication limits](https://firebase.google.com/docs/auth/limits), [Firestore pricing](https://firebase.google.com/docs/firestore/pricing), and [Firebase Hosting quotas](https://firebase.google.com/docs/hosting/usage-quotas-pricing).

## Firebase deployment

The deployed demo is available at [https://eirag-rag-261106-a7c9.web.app](https://eirag-rag-261106-a7c9.web.app). Firebase project `eirag-rag-261106-a7c9` has email/password Authentication, a Standard `(default)` Firestore database in `asia-south1` (Mumbai), owner-scoped Firestore rules, and Firebase Hosting. The project has no billing account attached. Firebase Web configuration is kept in the ignored local file `frontend/.env.local`; use [frontend/.env.example](frontend/.env.example) as a template when building locally, and never put service-account credentials or private API secrets in the frontend.

The live smoke check confirmed that the site loads and the sign-in/create-account interface renders. Registration was not submitted, so real mailbox delivery and a signed-in Firestore read/write were not verified. The project uses a real email verification link, not a numeric OTP. Real phone SMS OTP is outside this no-billing setup.

The Firebase project alias is recorded in [.firebaserc](.firebaserc). The deployed Firestore rules passed Firebase's compiler and five simulated allow/deny read cases. The security review is still a prototype review, not a production certification; see [docs/BUILD-STATUS.md](docs/BUILD-STATUS.md).

## Original local Docker app

The original backend-based app remains available for local development. It uses FastAPI, PostgreSQL, Qdrant, and local file storage, and is not the Firebase-hosted app. Read [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the local stack and data lifecycle. Do not use the legacy `docker-compose.cloud.yml` as a $0 cloud recipe.

## Production boundary

This is a demonstration build, not a production financial service. It has no numeric OTP, real SMS verification, organization membership, managed abuse controls, formal security review, financial benchmark, backup/restore exercise, or production monitoring. Do not upload confidential investor or customer records until data handling, retention, regional requirements, and controls have been reviewed.

See [docs/FREE-TIER-PLAN.md](docs/FREE-TIER-PLAN.md), [docs/PRODUCTION-FIT.md](docs/PRODUCTION-FIT.md), and [docs/BUILD-STATUS.md](docs/BUILD-STATUS.md) for the detailed scope and checks.

# Strict-$0 Firebase prototype

## Selected profile

- Domain: financial
- Target: investor demonstration
- Hosting/data provider: Firebase on the no-cost Spark plan
- Approach: upgrade the existing project with a static Firebase frontend
- Spend: billing status was checked; no billing account is attached and no billing link was created

This is a constrained prototype, not a production financial service. Firebase Spark quotas are limited and can pause service when exceeded. The Google Cloud Free Tier is not used because it requires Cloud Billing and does not provide a guaranteed hard spending cap.

## Current setup

Google Cloud project `eirag-rag-261106-a7c9` is now a Firebase project. Email/password Authentication is enabled, the default Standard Firestore database is active in `asia-south1` (Mumbai), the prototype rules are deployed, and the static site is live at [https://eirag-rag-261106-a7c9.web.app](https://eirag-rag-261106-a7c9.web.app). Billing is not enabled and no billing account is attached. Firestore location is permanent after creation. No financial corpus should be uploaded until the data-location and handling decision has been reviewed.

## Architecture implemented

| Area | Implementation | Limits |
|---|---|---|
| Web hosting | Next.js static export for Firebase Hosting | No server routes or always-on API |
| Accounts | Firebase Authentication email/password; email verification link required for workspace access | No numeric email OTP or phone SMS |
| Account data | Cloud Firestore client SDK, scoped under the authenticated user's UID | Firestore Spark quota applies |
| Access rules | Owner-only Firestore rules; only verified accounts can access their own records | No organization roles or shared workspaces |
| Document processing | Browser extraction for PDF, DOCX, TXT, CSV | 5 MB/file, 40,000 extracted characters/file, 20 chunks/file |
| Search | Browser-side lexical word overlap and source excerpts | No embeddings, semantic retrieval, or generative answer |
| Workspace caps | Fixed Firestore slots and rules cap each account at 50 documents, 20 chunks/file (1,000 total), 50 conversations, and 100 messages/conversation | No global rate limit across accounts; project Spark quotas are shared |
| Original files | Not archived; only extracted text and metadata are saved | User must retain original copies |
| AI model | None | No model charges or external inference |

Firebase Authentication stores password credentials. The application stores extracted text, document metadata, conversation messages, and citations in Firestore. Firestore quotas are currently 1 GiB stored data, 50,000 reads/day, 20,000 writes/day, and 20,000 deletes/day for qualifying databases. See [Firestore pricing](https://firebase.google.com/docs/firestore/pricing). Firebase Hosting also has storage and transfer quotas; see [Hosting usage and pricing](https://firebase.google.com/docs/hosting/usage-quotas-pricing).

## Authentication decision

Firebase's default email verification sends a one-time link, not a numeric email code. Real phone verification SMS is not included in this no-billing profile; Firebase's phone provider requires a billing-backed plan for real SMS delivery. Test phone numbers are not a substitute for real-user SMS. See [Firebase Authentication limits](https://firebase.google.com/docs/auth/limits) and [Authentication FAQ](https://firebase.google.com/docs/auth/faq-and-troubleshooting).

The app does not claim that SMS or numeric email OTP works. If either exact OTP requirement is mandatory, this project needs a costed provider and an abuse/rate-limit design before it can be added.

## Deployment completed

The live demo URL is [https://eirag-rag-261106-a7c9.web.app](https://eirag-rag-261106-a7c9.web.app). Authentication, the Firestore database, deployed security rules, and Hosting were provisioned without attaching billing. The app was built with the project's Firebase web settings, and the public page was smoke-checked in a browser. The registration flow was not submitted, so real mailbox delivery and signed-in data operations still need an owner-run check.

The local Firebase web settings are in ignored `frontend/.env.local` and are intentionally excluded from the source archive. Use `frontend/.env.example` to configure another local checkout. Do not use a service-account key in the browser or place any private credential in the web app's environment variables.

## What is still outside the $0 profile

- Real phone SMS OTP or numeric email OTP delivery
- Production-grade RAG model, vector database, or server-side processing
- Cloud archive of original files
- Organization SSO, shared workspaces, MFA enforcement, tenant administration
- Rate limiting and global storage quotas that resist account abuse
- Formal privacy, threat, compliance, load, backup/restore, and disaster-recovery review
- Production monitoring, incident response, and support

See [PRODUCTION-FIT.md](PRODUCTION-FIT.md) and [BUILD-STATUS.md](BUILD-STATUS.md) before using confidential or business-critical financial data.

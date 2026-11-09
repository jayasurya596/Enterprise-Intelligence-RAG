# Cloudflare-backed low-cost deployment

## Selected profile

- Domain: financial
- Website: Cloudflare Worker static assets
- Identity: Firebase Authentication email/password with verification link
- Workspace backend: Cloudflare Workers, D1, Vectorize, and Workers AI
- Spend goal: minimize cost and stay within included allowances where possible; not a guaranteed $0 account
- Website and Worker: deployed
- Original Docker/FastAPI/PostgreSQL/Qdrant stack: retained for local development

## Cloud services

| Function | Service | Data |
|---|---|---|
| Static site and API | Cloudflare Workers | Public client files and authenticated API routes |
| Sign-in credentials | Firebase Authentication | Email, password credential, verification status |
| Workspace profile | Cloudflare D1 | Firebase UID and verified email |
| Workspace content | Cloudflare D1 | Extracted document text, metadata, chats, messages, citations |
| Semantic retrieval | Cloudflare Vectorize | 384-dimensional embeddings plus owner/document/chunk metadata |
| Embeddings and answers | Workers AI | Document/query embeddings and retrieved answer context |
| Original files | Browser only | Not archived |

On first verified sign-in, any old Firestore workspace records are copied to D1 and Vectorize. Firestore is kept as the migration source. The Worker never receives or stores a password. Firebase Authentication remains the identity provider to preserve existing accounts; the site and RAG backend now run on Cloudflare.

## Limits and cost control

The app enforces 50 documents, 20 chunks/document, 1,000 total chunks, 50 conversations, 100 messages/conversation, and the file extraction limits of 5 MB and 40,000 characters.

The Worker uses BGE Small embeddings and the currently listed Llama 3.3 70B FP8 Fast answer model. It tracks an application-wide daily AI budget: 250,000 embedding input characters, 50,000 generation input characters, and 5,000 reserved output tokens. If a budget is reached, answer generation falls back to source excerpts; indexing reports a limit error until the next UTC day.

Cloudflare's published Workers AI allowance is 10,000 neurons/account/day; on Workers Paid, usage above that is billed. The app budget cannot see usage from other Workers on the same account, so it cannot promise a $0 invoice by itself. D1 and Vectorize also have finite included quotas. Review [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/), [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/), and [Vectorize pricing](https://developers.cloudflare.com/vectorize/platform/pricing/), and monitor Cloudflare account usage before broad sharing.

## Verification and OTP

Firebase sends an email verification link to the actual email address. Numeric email OTP and real phone SMS OTP are not active. Cloudflare Email Service requires a domain configured with Cloudflare DNS, and no domain was available during setup. SMS needs a separate provider. Adding these exact OTP methods requires provider configuration and may add cost.

## Data location and limitations

Cloudflare created D1 in APAC. This is not a financial-data residency or compliance review. The site is a demo, not a production financial service. No formal threat model, regulated-data assessment, global abuse limit, financial answer benchmark, or backup/restore exercise has been completed.

## Local configuration

frontend/.env.local and root .env are local ignored files. They contain public Firebase web settings and the Cloudflare Worker URL; they do not contain a Firebase service-account private key. Do not commit them.

See DEPLOYMENT.md for rebuild steps.

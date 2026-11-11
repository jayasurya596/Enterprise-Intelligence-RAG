# Cloudflare-backed low-cost deployment

## Selected profile

- Domain: financial
- Website: Cloudflare Worker static assets, protected by Cloudflare Access
- Sign-in: Cloudflare Access One-time PIN to email
- Workspace backend: Cloudflare Workers, D1, Vectorize, and Workers AI
- Spend goal: use free tiers and included allowances; not a guaranteed $0 invoice
- Custom domain: not required
- SMS: intentionally omitted to keep the setup email-only and cost-free

## Cloud services

| Function | Service | Data |
|---|---|---|
| Site, API, and edge gate | Cloudflare Workers and Access | Static assets, API routing, verified email session |
| Email login | Cloudflare Access One-time PIN | Email address and Access session; no app password |
| Workspace profile | Cloudflare D1 | Normalized email and stable workspace owner ID |
| Workspace content | Cloudflare D1 | Extracted document text, metadata, chats, messages, citations |
| Semantic retrieval | Cloudflare Vectorize | 384-dimensional embeddings and owner/document/chunk metadata |
| Embeddings and answers | Workers AI | Document/query embeddings and retrieved answer context |
| Original files | Browser only | Not archived |

The Worker validates the Access assertion's signature, issuer, audience, and expiry. On the first signed-in API request it creates a D1 profile row. When a previous D1 profile has the same email, the Worker reuses its owner ID. The new Access flow does not require Firebase passwords.

The Access policy currently allows everyone. Any person who controls a real email inbox can receive a code and create a separate workspace. If access should be limited to an interviewer or a team, change the policy to specific email addresses or an approved domain.

The old Firebase Hosting copy is a legacy page and is not the supported sign-in site. Firestore-only content is not automatically copied by Cloudflare Access. The latest read-only D1 count on 2026-11-11 was 1 user, 0 documents, and 1 conversation; no Cloudflare document upload was present then.

## Application limits

- 5 MB maximum file
- 40,000 extracted characters per file
- 20 chunks per document
- 50 documents and 1,000 chunks per account
- 50 conversations per account
- 100 messages per conversation
- Daily app AI budget: 250,000 embedding input characters, 50,000 generation input characters, and 5,000 reserved output tokens; resets at 00:00 UTC

When an AI budget is reached, answer generation falls back to source excerpts; indexing reports a limit error until the next UTC day.

## Free-tier and cost notes

Cloudflare Zero Trust Free supports up to 50 users. Cloudflare's setup guide says its Free plan is not charged, but onboarding may ask for payment details. Review the plan shown in your account before sharing broadly.

Workers AI, D1, and Vectorize have finite included quotas. The app's AI budget applies only to this Worker and cannot see usage from other Cloudflare services in the account. If the account is on a paid plan or exceeds included limits, charges may apply. Monitor the account-level usage dashboard. See [Cloudflare Zero Trust plans](https://www.cloudflare.com/plans/zero-trust-services/), [Cloudflare One setup](https://developers.cloudflare.com/cloudflare-one/setup/), [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/), [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/), and [Vectorize pricing](https://developers.cloudflare.com/vectorize/platform/pricing/).

## Email OTP behavior

Cloudflare Access sends a numeric one-time PIN to an email address allowed by the policy. A PIN is single-use, and a new PIN invalidates the previous one. The project owner reports successful email sign-in and answers. The latest D1 count was 1 user, 0 documents, and 1 conversation, so document ingestion and cited retrieval still need acceptance.

No phone OTP is configured. Cloudflare Access emails codes to the original address typed by the user, so this setup does not need a custom email domain.

## Data location and limitations

Cloudflare created D1 in APAC. This is not a financial-data residency or compliance review. The site is a demo, not a production financial service. No formal threat model, regulated-data assessment, global abuse limit, financial answer benchmark, or backup/restore exercise has been completed.

## Local configuration

frontend/.env.local contains the public Worker URL and the selected auth mode. Root .env contains local settings and a private provisioning token. Both files are ignored by Git and must remain private. Do not put the API token in a browser variable or Docker frontend build argument.

See DEPLOYMENT.md for rebuild steps.

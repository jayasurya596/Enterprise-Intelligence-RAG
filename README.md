# Enterprise Intelligence RAG

## Live site

- Secure website and API: [enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev](https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev)
- Cloudflare Access team login: [floral-waterfall-2ff2.cloudflareaccess.com](https://floral-waterfall-2ff2.cloudflareaccess.com)

The website and API run on one Cloudflare Worker. Cloudflare Access protects the whole Worker and sends a one-time email code to sign in. The current Access policy allows any email address that can receive the code. Use the Worker link above; the older Firebase Hosting copy is not the current sign-in site.

## What it does

- Cloudflare Access verifies each user through an email one-time PIN. No app password is collected or stored.
- On the first authenticated API request, the Worker creates a D1 profile for that email. Workspace data is isolated by user.
- Cloudflare D1 stores profiles, extracted document text, metadata, conversations, messages, citations, and daily AI counters.
- Cloudflare Vectorize stores 384-dimensional document embeddings and searches only within the signed-in user's vectors.
- Cloudflare Workers AI uses BGE Small embeddings and Llama 3.3 to draft answers from retrieved source excerpts.
- PDF, DOCX, TXT, and CSV text extraction runs in the browser. Limits are 5 MB, 40,000 extracted characters, and 20 chunks per document. Original files are not archived.
- Per-user limits are 50 documents, 1,000 chunks, 50 conversations, and 100 messages per conversation.

The Worker verifies the signed Cloudflare Access assertion, its issuer, signature, expiry, and application audience. Existing D1 workspaces are matched by email. A later read-only check on 2026-11-11 found 1 user, 0 documents, 1 conversation, 2 messages. This confirms workspace and chat activity; no Cloudflare document upload was present in D1 at that time.

The old Firebase Hosting copy may still display its previous Firebase sign-in flow. It is not the supported way to open the Cloudflare Access workspace. Old Firestore-only records are not automatically imported by the Access login flow.

## Data flow and privacy

The browser extracts file text and sends it over HTTPS to the Worker after Access sign-in. The Worker verifies the Access identity, saves text and workspace records in D1, writes embeddings to Vectorize, and sends questions plus retrieved excerpts to Workers AI when drafting answers. Review provider terms, retention, region, and security requirements before uploading confidential financial or customer data.

## Email OTP and cost

Email OTP is enabled through Cloudflare Access, with no custom domain and no SMS provider. Cloudflare's Free Zero Trust plan supports up to 50 users; account setup may ask for payment details, while Cloudflare says the Free plan is not charged. Workers AI, D1, and Vectorize have finite included quotas, so this project cannot guarantee a $0 invoice if limits are exceeded or the account is on a paid plan. See [Cloudflare Zero Trust plans](https://www.cloudflare.com/plans/zero-trust-services/) and the [Cloudflare One setup guide](https://developers.cloudflare.com/cloudflare-one/setup/).

The site redirects unauthenticated visitors to Cloudflare Access. The project owner reports successful email sign-in and receiving answers. The latest read-only D1 check found 1 user, 0 documents, 1 conversation, 2 messages, so document upload/indexing and a cited, document-grounded answer still need acceptance.

This is a demonstration build, not a certified financial product. Formal security, compliance, load, backup/restore, and financial answer-quality reviews have not been completed.

## Rebuild and deploy

In frontend/.env.local, set:

~~~text
NEXT_PUBLIC_AUTH_MODE=cloudflare-access
NEXT_PUBLIC_CLOUDFLARE_API_URL=https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev
~~~

Run from the repository root:

~~~text
cd frontend
npm ci
npm run lint
npm run build:static

cd ../cloudflare/rag-api
npm ci
npm run typecheck
npm run deploy
~~~

The Access team domain and application audience used for JWT validation are in cloudflare/rag-api/wrangler.jsonc. Keep them aligned with the Access application. The root .env contains local provisioning settings including a private Cloudflare API token. Keep .env and frontend/.env.local out of GitHub.

For local Access simulation, Wrangler has a development identity in its config. Run the Worker with ACCESS_APP_AUD set to local-development-audience. This simulated identity is for local development only.

## Project layout

- frontend/ — static Next.js workspace UI and file extraction
- cloudflare/rag-api/ — authenticated Worker, D1 migrations, Vectorize and Workers AI integration
- backend/ — original local FastAPI/PostgreSQL/Qdrant service, retained for development/evaluation
- docs/BUILD-STATUS.md — deployment and QA evidence
- docs/DEPLOYMENT.md — rebuild and service notes
- docs/FREE-TIER-PLAN.md — cost and free-tier notes
- docs/PRODUCTION-FIT.md — gaps before financial or business-critical use
- docs/PROJECT-DOCUMENTATION.md — full architecture, data flow, API, setup, and verification manual
- docs/INTERVIEW-GUIDE.md — interview pitch, demo outline, and likely questions
- docs/Enterprise-Intelligence-RAG-Project-Documentation.docx — Word edition of the full project manual
- docs/Enterprise-Intelligence-RAG-Interview-Guide.docx — Word edition of the interview guide
- docs/PROJECT-AND-INTERVIEW-GUIDE.md — project overview and interviewer preparation

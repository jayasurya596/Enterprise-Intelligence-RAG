# Enterprise Intelligence RAG

## Live site

- Website and API: [https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev](https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev)
- API readiness: [https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev/health/ready](https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev/health/ready)
- Previous Firebase Hosting address remains available as a fallback: [https://eirag-rag-261106-a7c9.web.app](https://eirag-rag-261106-a7c9.web.app)

The website assets and workspace API now run on Cloudflare Workers. Firebase Authentication still provides account identity and email/password sign-in so existing accounts remain usable; this is not a Cloudflare-only identity setup. Workspace requests require a valid Firebase ID token from an email-verified account.

## What it does

- Firebase Authentication handles email/password credentials and verifies account ownership with an email link.
- Cloudflare D1 stores verified user profile identifiers, extracted document text, metadata, conversations, messages, and citations.
- Cloudflare Vectorize stores 384-dimensional document embeddings and searches only within the authenticated owner’s vectors.
- Cloudflare Workers AI uses BGE Small embeddings and the current Llama 3.3 model to draft answers from retrieved source excerpts.
- PDF, DOCX, TXT, and CSV text extraction runs in the browser. Limits are 5 MB, 40,000 extracted characters, and 20 chunks per document. Original files are not archived.
- Per-account limits are 50 documents, 1,000 chunks, 50 conversations, and 100 messages per conversation.
- On first verified sign-in, any earlier Firestore documents and conversations are copied to Cloudflare. The source records remain in Firestore.

Passwords remain in Firebase Authentication. Cloudflare stores the authenticated UID and email for workspace ownership; it never stores the password.

## Data flow and privacy

The browser extracts text, then sends the chunks over HTTPS to the Worker. The Worker verifies the Firebase token, saves workspace data in D1, writes embeddings to Vectorize, and sends questions plus retrieved excerpts to Workers AI when drafting answers. Do not upload confidential financial or customer data until your organization has reviewed provider terms, retention, region, and security requirements.

## Account and OTP behavior

Verification uses a link delivered to the actual email address. Numeric email OTP and phone SMS OTP are not configured. Cloudflare Email Sending needs a domain onboarded to Cloudflare DNS; no domain is configured for this project. Real SMS also needs a delivery provider.

## Cost and service limits

This deployment is configured for low-cost use, not unlimited guaranteed $0 usage. D1 and Vectorize have free allowances. Workers AI provides 10,000 neurons per account per day; use above that on Workers Paid is billable. The app has a daily AI budget, but cannot account for other Cloudflare Workers using the same account. Check your plan and AI usage dashboard before sharing broadly. [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/), [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/), [Vectorize pricing](https://developers.cloudflare.com/vectorize/platform/pricing/).

This is a demonstration build, not a certified financial product. Formal security, compliance, load, backup/restore, and financial answer-quality reviews have not been completed.

## Rebuild and deploy

Local ignored files frontend/.env.local and root .env contain Firebase web settings and the Cloudflare API URL. Do not commit them.

    cd frontend
    npm ci
    npm run lint
    npm run build:static

    cd ../cloudflare/rag-api
    npm ci
    npm run typecheck
    npm run deploy

The deployed Worker serves the static frontend from frontend/out and routes API requests to the same Worker. Firebase Hosting remains available as a fallback. Local Docker users can run docker compose up --build -d from the repository root. Build arguments read Firebase web settings and the Cloudflare API URL from the ignored root .env.

## Project layout

- frontend/ — static Next.js website and Firebase sign-in
- cloudflare/rag-api/ — authenticated Worker, D1 migrations, Vectorize and Workers AI integration
- backend/ — original local FastAPI/PostgreSQL/Qdrant service, retained for local development/evaluation
- docs/BUILD-STATUS.md — deployment and QA evidence
- docs/DEPLOYMENT.md — rebuild and service notes
- docs/PRODUCTION-FIT.md — gaps before financial or business-critical use

# Deployment and data persistence

## Hosted website

- Public website and API: [https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev](https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev)
- Previous Firebase Hosting address (fallback): [https://eirag-rag-261106-a7c9.web.app](https://eirag-rag-261106-a7c9.web.app)
- Cloudflare D1: enterprise-intelligence-rag (APAC)
- Cloudflare Vectorize: enterprise-intelligence-rag-vectors
- Firebase project: eirag-rag-261106-a7c9

## Rebuild and deploy the Cloudflare site and API

From the repository root, build the static frontend first:

    cd frontend
    npm ci
    npm run lint
    npm run build:static

Then deploy the Worker with the generated frontend assets:

    cd ../cloudflare/rag-api
    npm ci
    npm run typecheck
    npm run deploy

The Worker serves the frontend at `/` and the RAG API at `/api/*`. Its readiness endpoint is `/health/ready`.

The D1 database and Vectorize index are provisioned. The current schema includes tenant-scoped document, conversation, and message IDs. To apply future schema migrations:

    npx wrangler d1 migrations apply enterprise-intelligence-rag --remote

Keep the existing Worker name and bindings. The Worker URL is configured as NEXT_PUBLIC_CLOUDFLARE_API_URL in ignored local environment files.

## Firebase Hosting fallback

The primary site uses Cloudflare Workers static assets. Firebase Hosting remains published as a fallback. To rebuild it, run `npm run build:firebase` and deploy with the Firebase CLI.

Firebase credentials are managed by Firebase Authentication. Never put a service-account key in frontend configuration.

## Data behavior

Firebase Authentication stores sign-in credentials and enforces email verification with a link. The Worker validates signed Firebase ID tokens and uses the UID as the owner key. Cloudflare D1 stores verified profile fields, document text, metadata, conversations, messages, and citations. Vectorize stores embeddings. Workers AI receives source text for embedding and retrieved snippets/questions for answer generation.

The browser extracts PDF, DOCX, TXT, and CSV text. Original uploaded files are not archived. First verified sign-in imports prior Firestore workspace records; Firestore is not deleted. Current-app document deletion removes the D1 text and corresponding Vectorize vectors.

## Local Docker stack

The Docker frontend build receives Firebase web settings and the Cloudflare API URL from root .env. Rebuild with:

    docker compose config --quiet
    docker compose up --build -d
    docker compose ps

The original local FastAPI/PostgreSQL/Qdrant backend remains available for local development and evaluation. The hosted Cloudflare-backed website does not use FastAPI for its document/chat data.

## User verification and limitations

The deployed API passed readiness, unauthenticated rejection, and CORS checks. A real verified user session is still needed to verify signup email delivery and full workspace operations. Email verification is link-based, not numeric OTP. Real phone SMS OTP is not configured. Review FREE-TIER-PLAN.md and PRODUCTION-FIT.md before using sensitive financial data.

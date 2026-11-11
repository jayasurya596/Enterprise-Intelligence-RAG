# Deployment and data persistence

## Hosted website

- Secure website and API: [https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev](https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev)
- Cloudflare Access team domain: floral-waterfall-2ff2.cloudflareaccess.com
- Cloudflare D1: enterprise-intelligence-rag, APAC
- Cloudflare Vectorize: enterprise-intelligence-rag-vectors
- Firebase project: eirag-rag-261106-a7c9, retained for legacy compatibility

Cloudflare Access protects all routes on the Worker URL, including assets, API, and readiness. An unauthenticated browser is redirected to Cloudflare Access. The readiness endpoint is therefore not a public health check.

The Access application is named Enterprise Intelligence RAG - Email OTP. It uses the existing One-time PIN identity provider, automatically sends users to email-code sign-in, and has an allow-everyone policy. This permits any real email address to create its own isolated workspace. To make the site private to a smaller group, replace the policy with an email list or an approved email domain.

## Rebuild and deploy the Cloudflare site and API

From the repository root, make sure frontend/.env.local has the Worker URL and Access mode:

~~~text
NEXT_PUBLIC_AUTH_MODE=cloudflare-access
NEXT_PUBLIC_CLOUDFLARE_API_URL=https://enterprise-intelligence-rag-api.penchalajayasuryachappidi.workers.dev
~~~

Build the frontend first:

~~~text
cd frontend
npm ci
npm run lint
npm run build:static
~~~

Then deploy the Worker and assets:

~~~text
cd ../cloudflare/rag-api
npm ci
npm run typecheck
npm run deploy
~~~

Keep the Access team domain and audience tag in wrangler.jsonc aligned with the Access app. If the Access app is deleted and recreated, its audience tag changes and the Worker must be redeployed with the new tag.

Apply future schema migrations with:

~~~text
npx wrangler d1 migrations apply enterprise-intelligence-rag --remote
~~~

The root .env contains a provisioning API token and must never be committed or copied into frontend configuration. The token is not needed by the deployed Worker at runtime.

## Authentication and data behavior

Cloudflare Access sends a one-time PIN to the user's email. The policy allows every email address, so the first successful sign-in creates a D1 profile row. The Worker validates the Access assertion and keys the workspace by normalized email. If a matching D1 profile from the old Firebase-token flow exists, its owner ID is reused.

The browser extracts PDF, DOCX, TXT, and CSV text. Original uploaded files are not archived. D1 stores extracted text, document metadata, conversations, messages, and citations. Vectorize stores embeddings. Workers AI receives document text for embeddings and retrieved excerpts/questions for answer generation. Deleting a document removes its D1 text and its Vectorize vectors.

The older Firebase Hosting address remains published as a legacy copy; it is not the current Cloudflare Access sign-in route. Old Firestore-only records are not imported by the Access flow. At deployment, the Cloudflare D1 database had 0 users, documents, and conversations.

## Local development and Docker

Wrangler config includes a fake local Access identity, local-user@example.invalid. To use it, run Wrangler with ACCESS_APP_AUD set to local-development-audience. Do not use this simulated identity in production.

The Docker compose file starts the original FastAPI/PostgreSQL/Qdrant stack. It is a separate local-development/evaluation path; the hosted Cloudflare website uses the Worker, D1, Vectorize, and Workers AI.

## QA status

The frontend typecheck and static build pass. The Worker typecheck and Wrangler dry run pass. Local tests exercised a simulated Access identity, D1 profile creation, conversation/message persistence, separate-user isolation, and rejection of a malformed Access JWT.

The live website redirects unauthenticated visitors to Cloudflare Access. The project owner reports successful email sign-in and answers. A later read-only D1 query showed 1 user, 0 documents, 1 conversation, 2 messages, and 2 messages, so an uploaded-document retrieval/citation and deletion check is still needed. The Firebase Hosting copy does not provide the current Cloudflare Access flow.

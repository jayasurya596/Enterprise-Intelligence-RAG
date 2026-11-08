# Deployment and data persistence

## Hosted free demo

The strict-$0 Firebase demo is live at [https://eirag-rag-261106-a7c9.web.app](https://eirag-rag-261106-a7c9.web.app). It uses Firebase Hosting, Firebase Authentication, and Cloud Firestore on the Spark no-billing plan. The project is `eirag-rag-261106-a7c9`; the Standard Native Firestore `(default)` database is in `asia-south1` (Mumbai). No billing account is attached.

Email/password Authentication is enabled. The app requires a verified email link before workspace access. Firestore rules are deployed and have passed Firebase's compiler plus five simulated read allow/deny cases. A browser smoke check confirmed that the public sign-in and create-account screens render. Registration was not submitted, so real mailbox delivery and signed-in database operations remain unverified.

### Local rebuild

1. Install Node.js and npm.
2. Copy `frontend/.env.example` to `frontend/.env.local` and fill the public Firebase Web App values from the project owner’s Firebase Console. The current local values are ignored by Git and excluded from the handoff archive.
3. From the repository root, run:

    cd frontend
    npm install
    npm run lint
    npm run build:firebase

The source project includes Firebase configuration and rules. Re-deployment requires an authorized Firebase account and Firebase CLI; the live deployment was provisioned through Firebase APIs in this environment. Never put a service-account key in the frontend.

### Data behavior and limits

Firebase Authentication stores account credentials. Firestore stores extracted document text, metadata, conversation messages, and citations under each authenticated user's UID. Uploaded originals are processed in the browser and are not archived. Deleting a document removes its saved text chunks and metadata.

Firebase email verification sends a link, not a numeric email OTP. Real phone SMS OTP is not included in the no-billing profile. Firestore and Hosting quotas are limited; exhausting a Spark quota can pause service. Avoid confidential financial data until data residency, retention, and security are approved.

## Original local Docker deployment

The legacy local stack consists of the Next.js server app, FastAPI, PostgreSQL, and Qdrant. When Docker Desktop and Compose are available, run `docker compose up --build -d` from the repository root. Its API and web ports bind to loopback; its database, Qdrant, and upload data persist in local Docker volumes. This stack is not the Firebase-hosted demo.

The local email/password account flow does not verify email or phone ownership. Production-mode backend startup is intentionally blocked until verified identity is integrated. The old `docker-compose.cloud.yml` is a legacy reference requiring separately provisioned services; it is not a free deployment recipe.

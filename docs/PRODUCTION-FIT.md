# Financial RAG readiness review

## Decision

The requested strict-$0 profile has been implemented and deployed as a small Firebase demo at [https://eirag-rag-261106-a7c9.web.app](https://eirag-rag-261106-a7c9.web.app). It is **not production-ready for financial data**; see [BUILD-STATUS.md](BUILD-STATUS.md).

## Requirement status

| Requirement | Status | Notes |
|---|---|---|
| Financial domain | Partial | UI defaults to `financial`; no reviewed financial benchmark has been run. |
| Public access from an investor's laptop | Deployed | Firebase Hosting is live. Sign-in/create-account UI was smoke-checked in a browser. |
| Persistent accounts | Deployed, real registration unverified | Firebase Authentication email/password is enabled; registration was not submitted, so no live verification email was tested. |
| Verify original email address | Implemented in source | Uses Firebase email verification link. No numeric email OTP. |
| Verify original phone number | Excluded | Real Firebase SMS requires billing-backed service, contrary to strict $0. |
| Store workspace data | Implemented in source | Extracted text, metadata, chat, and citations are stored in a user's Firestore path with owner-only rules. No original files are archived. |
| RAG answers | Limited | Word-overlap matching returns cited source excerpts. No embedding model or generative answer is used. |
| Free account quotas | Limited | Firestore rules enforce fixed per-account slots: 50 documents, 20 chunks/document, 50 conversations, and 100 messages/conversation. There is no global per-project rate limit, so shared Spark quotas can still be exhausted. |
| Financial production controls | Not passing | No formal security, abuse, regulatory, availability, backup/recovery, or capacity review. |
| One-day timeline | Not a readiness claim | A target duration does not prove production suitability. |

## Security and data limitations

Prototype Firestore rules restrict data access to the signed-in, email-verified UID, validate supported document shapes, and use fixed path slots to bound one account's stored records. They are deployed; Firebase's compiler and five simulated read allow/deny cases passed. The emulator was not run and broader write-path testing is outstanding. They do not provide organization-level administration or a global per-project rate limit. Multiple accounts can still consume shared free quotas.

Do not upload confidential investor, customer, or company records until the business approves Google's terms, the Firestore data region, retention/deletion, backup, and access policy. The original uploaded file remains in the browser and is not a cloud archive. The saved extracted text and conversations are cloud data.

The local Docker app is separate from the Firebase version. Its existing email/password flow does not verify ownership and its production API startup gate remains fail-closed.

## What is needed before production use

- Decide whether real phone OTP, numeric email OTP, or email verification links satisfy the requirement; cost real SMS separately.
- Define organization roles, account recovery, abuse limits, global quotas, and administrative controls.
- Complete a threat model, security review, dependency monitoring, and incident response process.
- Review Firebase terms, data processing, retention, regional requirements, backups, and deletion.
- Build and review a human-labeled financial corpus and measure answer/retrieval quality.
- Run abuse, load, backup/restore, and recovery exercises.
- Select and cost durable storage and server-side processing if original files or semantic RAG are required.

This profile should be presented as an investor demonstration, not an enterprise or production financial service.

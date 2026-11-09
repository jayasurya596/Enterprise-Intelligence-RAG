"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  browserLocalPersistence,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  reload,
  sendEmailVerification,
  sendPasswordResetEmail,
  setPersistence,
  signInWithEmailAndPassword,
  signOut,
  User,
} from "firebase/auth";
import { addDocument, answerFromWorkspace, Citation, Conversation, createConversation, DocumentItem, listConversations, listDocuments, listMessages, Message, removeDocument, saveMessage } from "./lib/knowledge-store";
import { firebaseConfigured, getFirebaseClient } from "./lib/firebase-client";
import { migrateLegacyFirestoreWorkspace } from "./lib/legacy-migration";
import { cloudflareApiConfigured } from "./lib/cloudflare-client";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [registering, setRegistering] = useState(false);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeConversation, setActiveConversation] = useState("");
  const [question, setQuestion] = useState("");
  const [domains, setDomains] = useState("financial");
  const [uploadDomains, setUploadDomains] = useState("financial");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async (activeUser: User) => {
    const { db } = getFirebaseClient();
    await migrateLegacyFirestoreWorkspace(db, activeUser);
    const [docs, chats] = await Promise.all([listDocuments(activeUser), listConversations(activeUser)]);
    setDocuments(docs);
    setConversations(chats);
  }, []);

  useEffect(() => {
    if (!firebaseConfigured) {
      setLoading(false);
      return;
    }
    const { auth } = getFirebaseClient();
    void setPersistence(auth, browserLocalPersistence).catch(() => undefined);
    return onAuthStateChanged(auth, (activeUser) => {
      setUser(activeUser);
      setLoading(false);
      if (!activeUser?.emailVerified) {
        setDocuments([]);
        setConversations([]);
        setMessages([]);
        setActiveConversation("");
      }
    });
  }, []);

  useEffect(() => {
    if (!user?.emailVerified) return;
    let cancelled = false;
    setError("");
    refresh(user).catch((reason: Error) => {
      if (!cancelled) setError(reason.message || "Could not load your workspace.");
    });
    return () => { cancelled = true; };
  }, [user, refresh]);

  useEffect(() => {
    if (!user?.emailVerified || !activeConversation) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    const { db } = getFirebaseClient();
    listMessages(user, activeConversation).then((items) => {
      if (!cancelled) setMessages(items);
    }).catch((reason: Error) => {
      if (!cancelled) setError(reason.message || "Could not load this conversation.");
    });
    return () => { cancelled = true; };
  }, [user, activeConversation]);

  async function authenticate(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      const { auth } = getFirebaseClient();
      await setPersistence(auth, browserLocalPersistence);
      if (registering) {
        const credential = await createUserWithEmailAndPassword(auth, email.trim(), password);
        await sendEmailVerification(credential.user, { url: window.location.origin });
        setUser(credential.user);
        setNotice("We sent a verification link to your email. Open it, return here, then choose “I've verified my email”.");
        setPassword("");
      } else {
        const credential = await signInWithEmailAndPassword(auth, email.trim(), password);
        await reload(credential.user);
        setUser(credential.user);
        setPassword("");
        if (!credential.user.emailVerified) setNotice("Verify this email address before opening the workspace.");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sign-in failed. Check the email and password.");
    } finally {
      setBusy(false);
    }
  }

  async function checkEmailVerification() {
    if (!user) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await reload(user);
      const current = getFirebaseClient().auth.currentUser;
      if (current?.emailVerified) {
        await current.getIdToken(true);
        setUser(current);
        setNotice("Email verified. Your private workspace is ready.");
      } else {
        setNotice("The email is not verified yet. Open the latest message from Firebase and try again.");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not refresh verification status.");
    } finally {
      setBusy(false);
    }
  }

  async function resendVerification() {
    if (!user) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await sendEmailVerification(user, { url: window.location.origin });
      setNotice(`A new verification link was sent to ${user.email || "your email"}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send the verification email.");
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword() {
    if (!email.trim()) { setError("Enter your email address first."); return; }
    setBusy(true); setError(""); setNotice("");
    try {
      await sendPasswordResetEmail(getFirebaseClient().auth, email.trim());
      setNotice("If an account exists, Firebase sent a password reset link to that email.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send the reset email.");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    if (!firebaseConfigured) return;
    await signOut(getFirebaseClient().auth);
    setUser(null); setDocuments([]); setConversations([]); setMessages([]); setActiveConversation("");
  }

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!user || !file) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const item = await addDocument(user, file, uploadDomains.split(","));
      setNotice(`${item.source_name} was extracted and saved to your account.`);
      setFile(null); setUploadDomains("financial");
      await refresh(user);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteDocument(item: DocumentItem) {
    if (!user || !window.confirm(`Delete “${item.source_name}” and its saved searchable text?`)) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await removeDocument(user, item.id);
      setNotice(`${item.source_name} was deleted.`);
      await refresh(user);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Delete failed.");
    } finally {
      setBusy(false);
    }
  }

  async function ask(event: FormEvent) {
    event.preventDefault();
    if (!user || !question.trim()) return;
    if (activeConversation && messages.length >= 99) {
      setError("This conversation has reached its 100-message free limit. Start a new conversation to continue.");
      return;
    }
    setBusy(true); setError(""); setNotice("");
    try {
      const prompt = question.trim();
      const conversationId = activeConversation || await createConversation(user, prompt);
      if (!activeConversation) setActiveConversation(conversationId);
      await saveMessage(user, conversationId, "user", prompt);
      const result = await answerFromWorkspace(user, prompt, domains.split(",").map((item) => item.trim()).filter(Boolean));
      await saveMessage(user, conversationId, "assistant", result.answer, result.citations);
      setQuestion("");
      const [updatedMessages] = await Promise.all([listMessages(user, conversationId), refresh(user)]);
      setMessages(updatedMessages);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Search failed.");
    } finally {
      setBusy(false);
    }
  }

  const selectedConversation = conversations.find((item) => item.id === activeConversation);

  if (loading) return <main className="auth-shell"><div className="auth-card"><p className="eyebrow">PRIVATE KNOWLEDGE WORKSPACE</p><h1>Loading your account…</h1></div></main>;

  if (!firebaseConfigured || !cloudflareApiConfigured) return <main className="auth-shell"><div className="auth-card">
    <div className="brand-mark">EI</div><p className="eyebrow">BACKEND SETUP REQUIRED</p><h1>Connect your workspace.</h1>
    <p className="muted">The site needs its Firebase sign-in settings and Cloudflare API address before account creation can work. No private API secret belongs in this browser app.</p>
    <p className="tiny-note">Add the Firebase web settings and NEXT_PUBLIC_CLOUDFLARE_API_URL to <code>frontend/.env.local</code>, then build and deploy.</p>
  </div></main>;

  if (user && !user.emailVerified) return <main className="auth-shell"><div className="auth-card">
    <div className="brand-mark">EI</div><p className="eyebrow">VERIFY YOUR EMAIL</p><h1>Check your inbox.</h1>
    <p className="muted">A one-time verification link was sent to <strong>{user.email}</strong>. Open it, then return to this page. Only verified email accounts can access saved data.</p>
    {error && <p className="error">{error}</p>}{notice && <p className="notice success-notice">{notice}</p>}
    <button className="primary-button" disabled={busy} onClick={checkEmailVerification}>{busy ? "Checking…" : "I've verified my email"}</button>
    <button className="text-button" disabled={busy} onClick={resendVerification}>Resend verification link</button>
    <p className="tiny-note">This strict-free version verifies email with a link. It does not send numeric email codes or phone SMS.</p>
    <button className="text-button" onClick={logout}>Use another account</button>
  </div></main>;

  if (!user) return <main className="auth-shell">
    <div className="auth-card">
      <div className="brand-mark">EI</div>
      <p className="eyebrow">PRIVATE KNOWLEDGE WORKSPACE</p>
      <h1>Answers with evidence.</h1>
      <p className="muted">Create an account with your email, verify the link we send, then save documents and questions in your own workspace.</p>
      <form onSubmit={authenticate} className="stack-form">
        <label>Email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></label>
        <label>Password<input type="password" minLength={12} required value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={registering ? "new-password" : "current-password"} /></label>
        {error && <p className="error">{error}</p>}{notice && <p className="notice success-notice">{notice}</p>}
        <button className="primary-button" disabled={busy}>{busy ? "Please wait…" : registering ? "Create account" : "Sign in"}</button>
      </form>
      <p className="switch-auth">{registering ? "Already have an account?" : "New to the workspace?"} <button className="text-button" onClick={() => { setRegistering(!registering); setError(""); setNotice(""); }}>{registering ? "Sign in" : "Create account"}</button></p>
      {!registering && <button className="text-button" disabled={busy} onClick={resetPassword}>Forgot password?</button>}
      <p className="tiny-note">Email verification links only; phone SMS OTP is not part of the $0 plan. Passwords are managed by Firebase Authentication.</p>
    </div>
  </main>;

  return <main className="app-shell">
    <aside className="sidebar">
      <div className="brand-row"><div className="brand-mark small">EI</div><div><strong>Enterprise</strong><span>Intelligence</span></div></div>
      <button className="new-chat" onClick={() => { setActiveConversation(""); setMessages([]); }}>＋ <span>New conversation</span></button>
      <div className="side-section"><p className="eyebrow">RECENT</p>
        {conversations.slice(0, 8).map((item) => <button key={item.id} className={`conversation-link ${activeConversation === item.id ? "selected" : ""}`} onClick={() => setActiveConversation(item.id)}>{item.title}</button>)}
        {conversations.length === 0 && <p className="side-empty">Your questions will appear here.</p>}
      </div>
      <div className="account"><div className="avatar">{(user.email || "U").slice(0, 1).toUpperCase()}</div><div className="account-email">{user.email}</div><button title="Sign out" className="signout" onClick={logout}>↗</button></div>
    </aside>

    <section className="main-panel">
      <header className="topbar"><div><p className="eyebrow">YOUR KNOWLEDGE, CONNECTED</p><h2>Document intelligence</h2></div><div className="status-chip"><span className="status-dot" /> Private workspace</div></header>
      {(error || notice) && <div className={error ? "notice error-notice" : "notice success-notice"}>{error || notice}<button onClick={() => { setError(""); setNotice(""); }}>×</button></div>}
      <div className="workspace-grid">
        <section className="documents-panel">
          <div className="section-heading"><div><p className="eyebrow">SOURCE LIBRARY</p><h3>Your documents <span className="count-pill">{documents.length}</span></h3></div></div>
          <form className="upload-card" onSubmit={upload}>
            <label className="file-drop"><span className="upload-icon">↑</span><strong>{file ? file.name : "Add a document"}</strong><small>PDF, DOCX, TXT or CSV · 5 MB, 20 chunks max</small><input type="file" accept=".pdf,.docx,.txt,.csv" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
            <label className="compact-label">Domains<input placeholder="financial" value={uploadDomains} onChange={(event) => setUploadDomains(event.target.value)} /></label>
            <button className="primary-button" disabled={!file || busy}>{busy ? "Working…" : "Extract and save"}</button>
            <p className="tiny-note">Extracted text and chats are stored in your Cloudflare workspace. Search embeddings and generated answers use Cloudflare AI. Original files are not archived. Limits: 50 documents, 20 chunks each, 50 conversations, and 100 messages per conversation.</p>
          </form>
          <div className="document-list">
            {documents.map((item) => <article className="document-row" key={item.id}><div className="file-icon">{item.source_name.toLowerCase().endsWith(".pdf") ? "PDF" : item.source_name.split(".").pop()?.toUpperCase()}</div><div className="document-meta"><strong title={item.source_name}>{item.source_name}</strong><span>{item.chunk_count} chunks · {item.domain_labels.join(", ")}</span>{item.status === "failed" && <small className="error-text">{item.error_summary}</small>}</div><span className={`state state-${item.status}`}>{item.status}</span><button className="delete-button" title="Delete document" onClick={() => deleteDocument(item)}>×</button></article>)}
            {documents.length === 0 && <div className="empty-state"><div className="empty-orbit">⌁</div><strong>No sources yet</strong><span>Upload a small PDF, DOCX, TXT, or CSV to build your private library.</span></div>}
          </div>
        </section>

        <section className="chat-panel">
          <div className="chat-heading"><div><p className="eyebrow">ASK YOUR SOURCES</p><h3>{selectedConversation?.title || "What would you like to know?"}</h3></div><span className="secure-pill">⌑ Source-linked</span></div>
          <div className="messages" aria-live="polite">
            {messages.map((message) => <article key={message.id} className={`message message-${message.role}`}><div className="message-label">{message.role === "user" ? "YOU" : "ASSISTANT"}</div><p className="message-content">{message.content}</p>{message.citations?.length > 0 && <div className="citation-list"><span className="citation-heading">SOURCES</span>{message.citations.map((citation: Citation) => <details className="citation-card" key={citation.chunk_id}><summary><span className="citation-marker">{citation.marker}</span><span>{citation.document_name}{citation.page_number ? ` · page ${citation.page_number}` : ""}</span><span className="chevron">⌄</span></summary><p>{citation.excerpt}</p></details>)}</div>}</article>)}
            {!messages.length && <div className="welcome-state"><div className="spark">✳</div><h3>Ask across your sources</h3><p>Cloudflare combines semantic and keyword search, then drafts an answer from your saved sources with citations.</p><div className="suggestion-row"><button onClick={() => setQuestion("What are the key points in my documents?")}>Summarize key points <span>↗</span></button><button onClick={() => setQuestion("Which sources discuss the most important risks?")}>Find risks <span>↗</span></button></div></div>}
          </div>
          <form className="composer" onSubmit={ask}><label className="domain-filter">Domains<input value={domains} onChange={(event) => setDomains(event.target.value)} placeholder="financial" /></label><div className="composer-box"><textarea maxLength={6000} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question about your documents…" rows={2} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><div className="composer-bottom"><span>Text sent securely to Cloudflare for retrieval and saved to your account</span><button aria-label="Send question" className="send-button" disabled={!question.trim() || busy}>↑</button></div></div></form>
          <p className="privacy-footnote">AI answers can be inaccurate. Review the cited source excerpts; this tool does not provide financial advice. Email verification uses a link; numeric email OTP and SMS OTP are not configured.</p>
        </section>
      </div>
    </section>
  </main>;
}

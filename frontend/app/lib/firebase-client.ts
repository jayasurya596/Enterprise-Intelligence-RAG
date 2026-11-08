import { FirebaseApp, getApps, initializeApp } from "firebase/app";
import { Auth, getAuth } from "firebase/auth";
import { Firestore, getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

export const firebaseConfigured = Object.values(firebaseConfig).every((value) => Boolean(value));

let app: FirebaseApp | undefined;
let auth: Auth | undefined;
let db: Firestore | undefined;

export function getFirebaseClient(): { app: FirebaseApp; auth: Auth; db: Firestore } {
  if (!firebaseConfigured) {
    throw new Error("Firebase is not configured. Add the public web settings to frontend/.env.local before deploying.");
  }
  if (!app) app = getApps()[0] ?? initializeApp(firebaseConfig);
  auth ??= getAuth(app);
  db ??= getFirestore(app);
  return { app, auth, db };
}

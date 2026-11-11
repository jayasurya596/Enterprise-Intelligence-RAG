import { spawnSync } from "node:child_process";
import nextEnv from "@next/env";
const { loadEnvConfig } = nextEnv;

loadEnvConfig(process.cwd(), true);
const authMode = process.env.NEXT_PUBLIC_AUTH_MODE?.trim() || "cloudflare-access";
const required = ["NEXT_PUBLIC_CLOUDFLARE_API_URL"];
if (authMode !== "cloudflare-access") {
  required.push(
    "NEXT_PUBLIC_FIREBASE_API_KEY",
    "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN",
    "NEXT_PUBLIC_FIREBASE_PROJECT_ID",
    "NEXT_PUBLIC_FIREBASE_APP_ID",
  );
}
const missing = required.filter((name) => !process.env[name]);
if (missing.length) {
  console.error(`Missing settings for ${authMode} authentication: ${missing.join(", ")}. Update .env.local before building.`);
  process.exit(1);
}

process.env.NEXT_STATIC_EXPORT = "1";
const result = spawnSync(process.execPath, ["node_modules/next/dist/bin/next", "build"], { stdio: "inherit", env: process.env });
process.exit(result.status ?? 1);

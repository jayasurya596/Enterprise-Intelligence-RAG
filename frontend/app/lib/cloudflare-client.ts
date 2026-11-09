import type { User } from "firebase/auth";

const configuredUrl = process.env.NEXT_PUBLIC_CLOUDFLARE_API_URL?.trim().replace(/\/$/, "") || "";
export const cloudflareApiConfigured = Boolean(configuredUrl);

export async function cloudflareRequest<T>(user: User, path: string, options: RequestInit = {}): Promise<T> {
  if (!configuredUrl) throw new Error("The Cloudflare workspace API is not configured for this site.");
  const token = await user.getIdToken();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  headers.set("Authorization", "Bearer " + token);
  if (options.body !== undefined && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(configuredUrl + path, { ...options, headers, cache: "no-store" });
  } catch {
    throw new Error("Could not reach the Cloudflare workspace service. Check your connection and retry.");
  }
  let body: unknown;
  try { body = await response.json(); } catch { body = null; }
  if (!response.ok) {
    const message = body && typeof body === "object" && "error" in body && typeof body.error === "string" ? body.error : "The workspace request failed (" + response.status + ").";
    throw new Error(message);
  }
  return body as T;
}

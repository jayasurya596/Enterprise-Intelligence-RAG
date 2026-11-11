const configuredUrl = process.env.NEXT_PUBLIC_CLOUDFLARE_API_URL?.trim().replace(/\/$/, "") || "";
export const cloudflareApiConfigured = Boolean(configuredUrl);
export const cloudflareApiUrl = configuredUrl;
export const cloudflareAccessMode = process.env.NODE_ENV !== "development" && process.env.NEXT_PUBLIC_AUTH_MODE !== "firebase";

export type WorkspaceUser = {
  uid: string;
  email: string | null;
  emailVerified: boolean;
  authProvider?: "firebase" | "cloudflare-access";
  getIdToken?: (forceRefresh?: boolean) => Promise<string>;
};

export async function cloudflareRequest<T>(user: WorkspaceUser | null, path: string, options: RequestInit = {}): Promise<T> {
  if (!configuredUrl) throw new Error("The Cloudflare workspace API is not configured for this site.");
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (user?.getIdToken) headers.set("Authorization", "Bearer " + await user.getIdToken());
  if (options.body !== undefined && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(configuredUrl + path, { ...options, headers, credentials: "include", cache: "no-store" });
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

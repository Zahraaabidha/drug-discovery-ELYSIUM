export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const API_KEY = import.meta.env.VITE_API_KEY || "changeme";

console.log("[API] base URL:", API_BASE_URL);

export async function apiFetch(path: string, options?: RequestInit) {
  const headers = new Headers(options?.headers);
  headers.set("X-API-KEY", API_KEY);
  
  if (options?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Request failed");
  }

  const contentType = res.headers.get("content-type");

  if (contentType && contentType.includes("application/json")) {
    return res.json();
  }

  return {};
}
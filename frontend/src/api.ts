import type { InstagramStatus, Story } from "./types";

const TOKEN_KEY = "ah_token";

function apiOrigin(): string {
  if (!import.meta.env.PROD) return "";
  return String(import.meta.env.VITE_API_ORIGIN ?? "").replace(/\/$/, "");
}

export function publicUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("blob:")) {
    return path;
  }
  return `${apiOrigin()}${path}`;
}

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  else sessionStorage.removeItem(TOKEN_KEY);
}

export function apiError(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object" && "msg" in detail[0]) {
      return String((detail[0] as { msg: string }).msg);
    }
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(init.body instanceof FormData) && init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(publicUrl(path), { ...init, headers });
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!response.ok) {
    throw new Error(apiError(data, `Error ${response.status}`));
  }
  if (data === null && text) {
    throw new Error("Respuesta inválida del servidor");
  }
  return data as T;
}

export function login(username: string, password: string) {
  return request<{ access_token: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout() {
  return request<void>("/api/auth/logout", { method: "POST" });
}

export function me() {
  return request<{ username: string }>("/api/auth/me");
}

export function listStories(status?: Story["status"]) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<Story[]>(`/api/stories${query}`);
}

export function createStory(file: File, scheduledAt: string) {
  const body = new FormData();
  body.append("file", file);
  body.append("scheduled_at", scheduledAt);
  return request<Story>("/api/stories", { method: "POST", body });
}

export function deleteStory(id: string) {
  return request<void>(`/api/stories/${id}`, { method: "DELETE" });
}

export function instagramStatus() {
  return request<InstagramStatus>("/api/instagram/status");
}

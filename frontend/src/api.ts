export type Status = "unread" | "read" | "archived" | "failed";

export interface Tag {
  id: string;
  name: string;
}

export interface Bookmark {
  id: string;
  title: string;
  url: string;
  description?: string | null;
  status: Status;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  tags: Tag[];
  content?: { title?: string; body?: string; raw_text?: string } | null;
  site_name?: string | null;
  logo_url?: string | null;
  image_url?: string | null;
  excerpt?: string | null;
  genres: string[];
  is_favorite: boolean;
}

export interface User {
  id: string;
  email: string;
  is_active: string;
  created_at: string;
}

export interface SearchResult {
  bookmark_id: string;
  title: string;
  url: string;
  chunk: string;
  distance?: number | null;
}

export interface Citation {
  bookmark_id: string;
  title: string;
  url: string;
}

export interface Insights {
  total: number;
  favorites: number;
  ready: number;
  unread: number;
  genres: { name: string; count: number }[];
  activity: { date: string; count: number }[];
  recommendations: string[];
}

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");
export const GOOGLE_AUTH_URL = import.meta.env.VITE_GOOGLE_AUTH_URL || `${API_URL}/auth/google`;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("arkive_token");
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : message;
    } catch {
      // Keep the HTTP status when the server does not return JSON.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string) =>
    request<User>("/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: async (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password });
    return request<{ access_token: string; token_type: string }>("/login", {
      method: "POST",
      body: form,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
  me: () => request<User>("/users/me"),
  bookmarks: (skip = 0, limit = 100) => request<Bookmark[]>(`/bookmarks?skip=${skip}&limit=${limit}`),
  bookmark: (id: string) => request<Bookmark>(`/bookmarks/${id}`),
  createBookmark: (payload: { title: string; url: string; description?: string }) =>
    request<Bookmark>("/bookmarks", { method: "POST", body: JSON.stringify(payload) }),
  updateBookmark: (id: string, payload: Partial<Pick<Bookmark, "title" | "url" | "description" | "status" | "genres" | "is_favorite">>) =>
    request<Bookmark>(`/bookmarks/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteBookmark: (id: string) => request<void>(`/bookmarks/${id}`, { method: "DELETE" }),
  addTags: (id: string, tags: string[]) =>
    request<Bookmark>(`/bookmarks/${id}/tags`, {
      method: "POST",
      body: JSON.stringify(tags.map((name) => ({ name }))),
    }),
  genres: () => request<string[]>("/genres"),
  insights: () => request<Insights>("/insights"),
  search: (query: string, topK = 20) =>
    request<{ results: SearchResult[] }>(`/search?q=${encodeURIComponent(query)}&top_k=${topK}`),
  chat: (question: string, topK = 8) =>
    request<{ answer: string; citations: Citation[] }>("/chat", {
      method: "POST",
      body: JSON.stringify({ question, top_k: topK }),
    }),
};

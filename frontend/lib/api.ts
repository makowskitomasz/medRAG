import { getToken, getRefreshToken, saveToken, clearAuth } from "./auth";

const BASE = "/api";

let _refreshPromise: Promise<boolean> | null = null;

async function _tryRefresh(): Promise<boolean> {
  const rt = getRefreshToken();
  if (!rt) return false;
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: rt }),
    });
    if (!res.ok) return false;
    const data: { access_token: string; refresh_token?: string } = await res.json();
    saveToken(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  authenticated = true,
  _retried = false
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (authenticated) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    if (res.status === 401 && authenticated && !_retried) {
      if (!_refreshPromise) {
        _refreshPromise = _tryRefresh().finally(() => { _refreshPromise = null; });
      }
      const refreshed = await _refreshPromise;
      if (refreshed) return request<T>(path, options, authenticated, true);
      clearAuth();
      if (typeof window !== "undefined") window.location.href = "/login";
    }
    let msg: string = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      if (typeof err.detail === "string") msg = err.detail;
      else if (Array.isArray(err.detail)) msg = err.detail.map((d: { msg?: string }) => d.msg).join(", ");
      else if (err.message) msg = err.message;
    } catch {} // ignore non-JSON error body
    throw new Error(msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/* ---- Auth ---- */
export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
}
export interface User {
  id: string;
  email: string;
  role: string;
  first_name?: string | null;
  last_name?: string | null;
}

export const auth = {
  login: (email: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }, false),
  register: (email: string, password: string, first_name?: string, last_name?: string) =>
    request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, first_name, last_name }),
    }, false),
  me: () => request<User>("/auth/me"),
  listUsers: () => request<User[]>("/auth/users"),
};

/* ---- Projects ---- */
export interface ProjectSettings {
  rag_mode: string;
  llm_model: string;
  chunking_strategy: string;
  embedding_provider: string;
  hybrid_alpha: number;
  top_k: number;
  rerank_top_n: number;
  prompt_overrides: Record<string, string>;
}
export interface Project {
  id: string;
  project_id: string; // alias populated by enrichProject
  name: string;
  description: string;
  settings: ProjectSettings;
  member_ids: string[];
  created_at: string;
  color?: string;
  initials?: string;
}
export interface CreateProjectInput {
  name: string;
  description?: string;
  rag_mode?: string;
  chunking_strategy?: string;
}

export interface UpdateProjectInput {
  name?: string;
  description?: string;
}

export interface UpdateSettingsInput {
  rag_mode?: string;
  llm_model?: string;
  chunking_strategy?: string;
  embedding_provider?: string;
  hybrid_alpha?: number;
  top_k?: number;
  rerank_top_n?: number;
  prompt_overrides?: Record<string, string>;
}

export interface EnumOption {
  value: string;
  label: string;
  description: string;
}

export interface FieldConstraint {
  type: string;
  min: number;
  max: number;
  step: number;
  default: number;
  description: string;
}

export interface PromptSlot {
  slug: string;
  label: string;
  description: string;
  default_template: string;
}

export interface SettingsOptions {
  rag_modes: EnumOption[];
  chunking_strategies: EnumOption[];
  embedding_providers: EnumOption[];
  llm_models: EnumOption[];
  hybrid_alpha: FieldConstraint;
  top_k: FieldConstraint;
  rerank_top_n: FieldConstraint;
  prompt_slots: PromptSlot[];
}

function projectColor(id: string): string {
  const colors = ["#7DD3FC", "#6EE7B7", "#A5B0E0", "#C7CEEA", "#FCA5A5", "#FCD34D"];
  let hash = 0;
  for (const c of id) hash = (hash * 31 + c.charCodeAt(0)) & 0xffffffff;
  return colors[Math.abs(hash) % colors.length];
}

function projectInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

function enrichProject(p: Project): Project {
  const pid = p.id ?? p.project_id ?? "";
  return {
    ...p,
    id: pid,
    project_id: pid,
    color: p.color ?? projectColor(pid),
    initials: p.initials ?? projectInitials(p.name),
  };
}

export const projects = {
  list: () => request<Project[]>("/admin/projects").then((ps) => ps.map(enrichProject)),
  get: (id: string) => request<Project>(`/admin/projects/${id}`).then(enrichProject),
  create: (data: CreateProjectInput) =>
    request<Project>("/admin/projects", { method: "POST", body: JSON.stringify(data) }).then(enrichProject),
  update: (id: string, data: UpdateProjectInput) =>
    request<Project>(`/admin/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }).then(enrichProject),
  updateSettings: (id: string, data: UpdateSettingsInput) =>
    request<Project>(`/admin/projects/${id}/settings`, { method: "PATCH", body: JSON.stringify(data) }).then(enrichProject),
  getSettingsOptions: () =>
    request<SettingsOptions>("/admin/projects/settings/options"),
  deletePromptOverride: (projectId: string, slug: string) =>
    request<Project>(`/admin/projects/${projectId}/settings/prompts/${slug}`, { method: "DELETE" }).then(enrichProject),
  delete: (id: string) =>
    request<void>(`/admin/projects/${id}`, { method: "DELETE" }),
  addMember: (projectId: string, userId: string) =>
    request<Project>(`/admin/projects/${projectId}/members/${userId}`, { method: "POST" }).then(enrichProject),
  removeMember: (projectId: string, userId: string) =>
    request<Project>(`/admin/projects/${projectId}/members/${userId}`, { method: "DELETE" }).then(enrichProject),
};

/* ---- Documents ---- */
export interface Document {
  document_id: string;
  filename: string;
  status: "uploaded" | "parsed" | "chunked" | "embedded" | "indexed" | "failed";
  created_at?: string;
  status_history: Array<{ status: string; timestamp?: string; ts?: string; error?: string | null }>;
  file_size?: number | null;
  page_count?: number | null;
  chunk_count?: number | null;
}

export interface DocumentsPage {
  items: Document[];
  total: number;
  page: number;
  limit: number;
}

export const documents = {
  listPage: async (projectId: string, page = 1, limit = 50): Promise<DocumentsPage> => {
    return request<DocumentsPage>(`/admin/projects/${projectId}/documents?page=${page}&limit=${limit}`);
  },
  list: async (projectId: string): Promise<Document[]> => {
    const res = await request<{ items: Document[]; total: number }>(`/admin/projects/${projectId}/documents?limit=100`);
    return res.items;
  },
  projectStats: (projectId: string) =>
    request<{ total_chunks: number; total_documents: number; indexed_count: number; failed_count: number }>(
      `/admin/projects/${projectId}/documents/stats`
    ),
  upload: async (projectId: string, file: File): Promise<Document> => {
    const token = getToken();
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/ingest/projects/${projectId}/documents`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed: ${res.status}`);
    }
    return res.json();
  },
  delete: (projectId: string, docId: string) =>
    request<void>(`/ingest/projects/${projectId}/documents/${docId}`, { method: "DELETE" }),
};

/* ---- Stream query ---- */
export interface QueryStreamRequest {
  project_id: string;
  query: string;
  conversation_id?: string | null;
  rag_mode_override?: string;
}

export interface ScannedDoc {
  name: string;
  hits: number;
  done: boolean;
}

export interface Citation {
  chunk_id: string;
  documentId?: string;
  n?: number;
  filename?: string | null;
  page?: number | null;
  snippet: string;
  relevance?: number;
}

export interface SearchEvent {
  type: "search";
  status: "start" | "done";
  count?: number;
  filenames?: string[];
  files?: Array<{ name: string; hits: number }>;
}

export interface ThinkEvent {
  type: "think";
  step: number;
  label: string;
  text: string;
  durationMs: number;
}

export interface StreamEvent {
  type: "meta" | "token" | "citation" | "citations" | "search" | "think" | "done" | "error" | string;
  // meta (mock)
  mode?: string;
  userMessageId?: string;
  aiMessageId?: string;
  // token
  content?: string;
  text?: string;       // mock uses `text`, backend uses `content`
  // citation (mock singular) and citations (backend batch)
  n?: number;
  documentId?: string;
  relevance?: number;
  citations?: Citation[];
  conversation_id?: string;
  rag_mode?: string;
  // search (mock: progress+docs, backend: status+files/filenames)
  progress?: number;
  docs?: ScannedDoc[];
  status?: "start" | "done";
  count?: number;
  filenames?: string[];
  /** Per-document chunk counts for the selected fragments. */
  files?: Array<{ name: string; hits: number }>;
  // think
  step?: number;
  label?: string;
  agent?: string;
  durationMs?: number;
  // done
  messageId?: string;
  timing?: { totalMs: number; searchMs: number; thinkMs: number; streamMs: number };
  usedChunkIds?: string[];
  // error / shared
  error?: string;
  page?: number | null;
  snippet?: string;
}

export async function streamQuery(
  req: QueryStreamRequest,
  onEvent: (ev: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const token = getToken();
  const res = await fetch(`${BASE}/chat/query/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Query failed: ${res.status}`);
  }
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Split on SSE block delimiter (\n\n)
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      if (!block.trim()) continue;

      let sseEventType = "";
      let dataStr = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) sseEventType = line.slice(7).trim();
        else if (line.startsWith("data: ")) dataStr = line.slice(6).trim();
      }
      if (!dataStr) continue;
      if (dataStr === "[DONE]") return;
      try {
        const parsed = JSON.parse(dataStr);
        // Backend format embeds type in JSON; mock format uses SSE `event:` line
        const ev: StreamEvent = {
          type: parsed.type ?? sseEventType ?? "unknown",
          ...parsed,
        };
        onEvent(ev);
      } catch {} // ignore malformed SSE lines
    }
  }
}

/* ---- Conversations ---- */
export interface ConversationMessage {
  role: string;
  content: string;
  citations?: Citation[];
  timestamp: string;
}

export interface ConversationSummary {
  id: string;
  project_id: string;
  user_id: string | null;
  rag_mode: string;
  message_count: number;
  first_user_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[];
}

export const conversations = {
  list: (projectId: string, limit = 50) =>
    request<ConversationSummary[]>(`/chat/conversations?project_id=${encodeURIComponent(projectId)}&limit=${limit}`),
  get: (id: string) =>
    request<ConversationDetail>(`/chat/conversations/${id}`),
};

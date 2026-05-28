const API_BASE = "/api/proxy"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })
  if (!res.ok) {
    const body = await res.text().catch(() => "")
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json()
}

// Auth
export const authApi = {
  login: (email: string, password: string) =>
    fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),

  me: () => fetch("/api/auth/me"),

  logout: () => fetch("/api/auth/logout", { method: "POST" }),
}

// Projects
export const projectsApi = {
  list: (): Promise<Project[]> => request("/projects"),
}

// Conversations
export const conversationsApi = {
  list: (projectId?: string): Promise<ConversationSummary[]> =>
    request(`/conversations${projectId ? `?project_id=${projectId}` : ""}`),

  get: (id: string): Promise<Conversation> => request(`/conversations/${id}`),

  patch: (id: string, title: string): Promise<ConversationSummary> =>
    request(`/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),

  delete: (id: string): Promise<void> =>
    request(`/conversations/${id}`, { method: "DELETE" }),
}

// Chat (non-streaming)
export const chatApi = {
  query: (body: QueryRequest): Promise<QueryResponse> =>
    request("/chat/query", { method: "POST", body: JSON.stringify(body) }),
}

// Types
export interface Project {
  project_id: string
  name: string
  description?: string
  settings: {
    rag_mode: string
    chunking_strategy: string
    top_k: number
    hybrid_alpha: number
    rerank_top_n: number
  }
  created_at: string
}

export interface ConversationSummary {
  id: string
  project_id: string
  title?: string
  rag_mode: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface Conversation extends ConversationSummary {
  messages: ConversationMessage[]
}

export interface ConversationMessage {
  role: "user" | "assistant"
  content: string
  timestamp: string
}

export interface QueryRequest {
  project_id: string
  query: string
  conversation_id?: string
  stream?: boolean
}

export interface Citation {
  n: number
  documentId: string
  filename?: string
  page?: number
  snippet: string
}

export interface QueryResponse {
  conversation_id: string
  answer: string
  citations: Citation[]
  rag_mode: string
}

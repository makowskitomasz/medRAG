"use client"

import { useCallback, useRef, useState } from "react"
import type { Citation } from "@/lib/api"

export type ChatPhase = "idle" | "searching" | "thinking" | "streaming" | "done" | "error"

export interface SearchEvent {
  status: "searching" | "reranking" | "done"
  query?: string
  found?: number
  kept?: number
}

export interface ThinkEvent {
  step: string
  note?: string
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  citations?: Citation[]
  ragMode?: string
  searchEvents?: SearchEvent[]
  thinkEvents?: ThinkEvent[]
}

interface StreamState {
  phase: ChatPhase
  messages: ChatMessage[]
  searchEvents: SearchEvent[]
  thinkEvents: ThinkEvent[]
  error: string | null
}

export function useChatStream(projectId: string | null, conversationId?: string) {
  const [state, setState] = useState<StreamState>({
    phase: "idle",
    messages: [],
    searchEvents: [],
    thinkEvents: [],
    error: null,
  })
  const abortRef = useRef<AbortController | null>(null)
  const convIdRef = useRef<string | undefined>(conversationId)

  const send = useCallback(
    async (query: string) => {
      if (!projectId) return
      abortRef.current?.abort()
      const abort = new AbortController()
      abortRef.current = abort

      // optimistically add user message
      const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: query }
      setState((s) => ({
        phase: "searching",
        messages: [...s.messages, userMsg],
        searchEvents: [],
        thinkEvents: [],
        error: null,
      }))

      const assistantId = crypto.randomUUID()
      let assistantContent = ""
      const citations: Citation[] = []
      const searchEvents: SearchEvent[] = []
      const thinkEvents: ThinkEvent[] = []

      try {
        const res = await fetch("/api/proxy/chat/query/stream", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({
            project_id: projectId,
            query,
            conversation_id: convIdRef.current,
            stream: true,
          }),
          signal: abort.signal,
        })

        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        if (!res.body) throw new Error("No response body")

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ""
        let currentEvent: string | null = null

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n")
          buffer = lines.pop() ?? ""

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim()
            } else if (line.startsWith("data: ")) {
              const raw = line.slice(6)
              if (raw === "[DONE]") break

              try {
                const data = JSON.parse(raw)

                switch (currentEvent) {
                  case "meta":
                    convIdRef.current = data.conversationId ?? convIdRef.current
                    break

                  case "search": {
                    const ev: SearchEvent = {
                      status: data.status,
                      query: data.query,
                      found: data.found,
                      kept: data.kept,
                    }
                    searchEvents.push(ev)
                    setState((s) => ({
                      ...s,
                      phase: "searching",
                      searchEvents: [...searchEvents],
                    }))
                    break
                  }

                  case "think": {
                    const ev: ThinkEvent = { step: data.step, note: data.note }
                    thinkEvents.push(ev)
                    setState((s) => ({
                      ...s,
                      phase: "thinking",
                      thinkEvents: [...thinkEvents],
                    }))
                    break
                  }

                  case "token":
                    assistantContent += data.text ?? ""
                    setState((s) => ({
                      ...s,
                      phase: "streaming",
                      messages: upsertAssistant(s.messages, assistantId, assistantContent, citations, searchEvents, thinkEvents),
                    }))
                    break

                  case "citation":
                    citations.push({
                      n: data.n,
                      documentId: data.documentId,
                      filename: data.filename,
                      page: data.page,
                      snippet: data.snippet,
                    })
                    setState((s) => ({
                      ...s,
                      messages: upsertAssistant(s.messages, assistantId, assistantContent, citations, searchEvents, thinkEvents),
                    }))
                    break

                  case "done":
                    convIdRef.current = data.conversationId ?? convIdRef.current
                    setState((s) => ({
                      ...s,
                      phase: "done",
                      messages: upsertAssistant(s.messages, assistantId, assistantContent, citations, searchEvents, thinkEvents),
                    }))
                    break

                  case "error":
                    throw new Error(data.message ?? "Stream error")
                }
              } catch (parseErr) {
                if (currentEvent === "error") throw parseErr
              }
            } else if (line === "") {
              currentEvent = null
            }
          }
        }

        // Finalize if done event wasn't sent
        setState((s) =>
          s.phase !== "done"
            ? {
                ...s,
                phase: "done",
                messages: upsertAssistant(s.messages, assistantId, assistantContent, citations, searchEvents, thinkEvents),
              }
            : s
        )
      } catch (err: unknown) {
        if ((err as Error)?.name === "AbortError") return
        setState((s) => ({
          ...s,
          phase: "error",
          error: (err as Error)?.message ?? "Nieznany błąd",
        }))
      }
    },
    [projectId]
  )

  const cancel = useCallback(() => {
    abortRef.current?.abort()
    setState((s) => ({ ...s, phase: "idle" }))
  }, [])

  return {
    ...state,
    conversationId: convIdRef.current,
    send,
    cancel,
  }
}

function upsertAssistant(
  messages: ChatMessage[],
  id: string,
  content: string,
  citations: Citation[],
  searchEvents: SearchEvent[],
  thinkEvents: ThinkEvent[]
): ChatMessage[] {
  const existing = messages.find((m) => m.id === id)
  if (existing) {
    return messages.map((m) =>
      m.id === id ? { ...m, content, citations, searchEvents, thinkEvents } : m
    )
  }
  return [
    ...messages,
    {
      id,
      role: "assistant",
      content,
      citations,
      searchEvents,
      thinkEvents,
    },
  ]
}

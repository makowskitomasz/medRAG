"use client";
import { useState, useRef, useCallback } from "react";
import { streamQuery, Citation, ScannedDoc, ConversationMessage } from "@/lib/api";
import { highestCitedIndex } from "@/lib/citations";

export type Phase = "idle" | "searching" | "thinking" | "streaming" | "done";

/** Mongo stores naive UTC, so an unsuffixed timestamp must not be read as local time. */
function parseUtc(iso: string): number {
  return Date.parse(/([zZ]|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : iso + "Z");
}

export interface ThinkStep {
  step: number;
  label: string;
  text: string;
  durationMs: number;
  agent?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "ai";
  text: string;
  /** Captured once when the message is created — rendering `new Date()` made the
   *  displayed time jump on every token. */
  createdAt?: number;
  citations?: Citation[];
  conversationId?: string;
  ragMode?: string;
  phase?: Phase;
  streamedText?: string;
  citationsRevealed?: number;
  thinkSteps?: ThinkStep[];
  searchDocs?: ScannedDoc[];
  searchProgress?: number;
  error?: string;
  timing?: { totalMs: number; searchMs: number; thinkMs: number; streamMs: number };
  /** Wall time from send to the last streamed token. */
  elapsedMs?: number;
  usedChunkIds?: string[];
}

interface UseChatStreamReturn {
  messages: ChatMessage[];
  phase: Phase;
  isGenerating: boolean;
  activeConversationId: string | null;
  send: (
    text: string,
    projectId: string,
    ragMode?: string,
    replaceLastExchange?: boolean
  ) => Promise<void>;
  /** Re-run the most recent question, replacing its answer. */
  regenerate: (projectId: string, ragMode?: string) => Promise<void>;
  /** Text of the last question — used to restore the composer after a failure. */
  lastQuery: string | null;
  stop: () => void;
  reset: () => void;
  loadHistory: (
    convId: string,
    ragMode: string,
    msgs: ConversationMessage[],
    meta?: { totalMessages?: number }
  ) => void;
  /** Total messages stored server-side; larger than `messages` when windowed. */
  totalMessages: number;
}

export function useChatStream(): UseChatStreamReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [totalMessages, setTotalMessages] = useState(0);
  const [lastQuery, setLastQuery] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const aiMsgIdRef = useRef<string>("");

  const isGenerating = phase === "searching" || phase === "thinking" || phase === "streaming";

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setPhase("done");
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setPhase("idle");
    setActiveConversationId(null);
    setTotalMessages(0);
    setLastQuery(null);
  }, []);

  const loadHistory = useCallback((
    convId: string,
    ragMode: string,
    msgs: ConversationMessage[],
    meta?: { totalMessages?: number }
  ) => {
    abortRef.current?.abort();
    setActiveConversationId(convId);
    setPhase("idle");
    setTotalMessages(meta?.totalMessages ?? msgs.length);
    setLastQuery([...msgs].reverse().find((m) => m.role === "user")?.content ?? null);
    setMessages(
      msgs.map((m, i) => ({
        id: `hist-${i}`,
        role: m.role === "user" ? "user" : "ai",
        text: m.content,
        createdAt: m.timestamp ? parseUtc(m.timestamp) : undefined,
        ragMode: m.role !== "user" ? ragMode : undefined,
        phase: "done" as Phase,
        citations: m.citations ?? [],
        citationsRevealed: m.citations?.length ?? 0,
      }))
    );
  }, []);

  const send = useCallback(async (
    text: string,
    projectId: string,
    ragMode?: string,
    /** Drop the previous question/answer pair first — used by regenerate. */
    replaceLastExchange = false,
  ) => {
    if (!text.trim() || !projectId) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const userMsgId = `u-${Date.now()}`;
    const aiMsgId = `a-${Date.now()}`;
    aiMsgIdRef.current = aiMsgId;
    setLastQuery(text);

    const pending: ChatMessage[] = [
      { id: userMsgId, role: "user", text, createdAt: Date.now() },
      {
        id: aiMsgId,
        role: "ai",
        text: "",
        createdAt: Date.now(),
        ragMode: ragMode,
        phase: "searching",
        streamedText: "",
        citationsRevealed: 0,
        citations: [],
        thinkSteps: [],
        searchDocs: [],
        searchProgress: 0,
      },
    ];
    setMessages((prev) => {
      if (!replaceLastExchange) return [...prev, ...pending];
      // Walk back past the trailing assistant reply and its question.
      const cut = [...prev];
      if (cut.at(-1)?.role === "ai") cut.pop();
      if (cut.at(-1)?.role === "user") cut.pop();
      return [...cut, ...pending];
    });
    setPhase("searching");

    const pendingCitations: Citation[] = [];
    const startedAt = performance.now();

    try {
      await streamQuery(
        {
          project_id: projectId,
          query: text,
          conversation_id: activeConversationId,
          rag_mode_override: ragMode,
        },
        (ev) => {
          if (aiMsgIdRef.current !== aiMsgId) return;

          if (ev.type === "meta") {
            // Mode info from mock SSE
            if (ev.mode) {
              setMessages((prev) =>
                prev.map((m) => m.id === aiMsgId ? { ...m, ragMode: ev.mode } : m)
              );
            }
          }

          if (ev.type === "search") {
            if (ev.docs) {
              // Mock format: incremental docs array with progress
              const searchDocs: ScannedDoc[] = ev.docs;
              const progress = ev.progress ?? 1;
              setPhase("searching");
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMsgId
                    ? { ...m, phase: "searching", searchDocs, searchProgress: progress }
                    : m
                )
              );
            } else if (ev.status === "start") {
              setPhase("searching");
              setMessages((prev) =>
                prev.map((m) => m.id === aiMsgId ? { ...m, phase: "searching" } : m)
              );
            } else if (ev.status === "done") {
              // Backend format: `files` carries per-document hit counts; `filenames`
              // is the older shape kept for compatibility.
              const searchDocs: ScannedDoc[] = ev.files
                ? ev.files.map((f) => ({ name: f.name, hits: f.hits, done: true }))
                : (ev.filenames ?? []).map((name) => ({ name, hits: 0, done: true }));
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMsgId
                    ? { ...m, searchDocs, searchProgress: 1 }
                    : m
                )
              );
            }
          }

          if (ev.type === "think") {
            setPhase("thinking");
            const step: ThinkStep = {
              step: ev.step ?? 0,
              label: ev.label ?? "",
              text: ev.text ?? "",
              durationMs: ev.durationMs ?? 0,
              agent: ev.agent,
            };
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== aiMsgId) return m;
                const existing = m.thinkSteps ?? [];
                const idx = existing.findIndex((s) => s.step === step.step);
                const updated =
                  idx >= 0
                    ? existing.map((s, i) => (i === idx ? step : s))
                    : [...existing, step];
                return { ...m, phase: "thinking", thinkSteps: updated };
              })
            );
          }

          // Backend: batch citations event
          if (ev.type === "citations") {
            pendingCitations.push(...(ev.citations ?? []));
            if (ev.conversation_id) setActiveConversationId(ev.conversation_id);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiMsgId
                  ? { ...m, ragMode: ev.rag_mode ?? m.ragMode, conversationId: ev.conversation_id }
                  : m
              )
            );
          }

          // Mock: individual citation event
          if (ev.type === "citation") {
            const cit: Citation = {
              chunk_id: ev.documentId ?? `cit-${ev.n ?? pendingCitations.length}`,
              documentId: ev.documentId,
              n: ev.n,
              page: ev.page ?? null,
              snippet: ev.snippet ?? "",
              relevance: ev.relevance,
            };
            pendingCitations.push(cit);
          }

          if (ev.type === "token") {
            const token = ev.text ?? ev.content ?? "";
            setPhase("streaming");
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== aiMsgId) return m;
                const newText = (m.streamedText ?? "") + token;
                // Scan the whole text, not just this token — a marker can straddle
                // two chunks. Marker variants live in lib/citations so the reveal
                // logic and the renderer can never drift apart.
                const revealed = Math.max(
                  m.citationsRevealed ?? 0,
                  highestCitedIndex(newText)
                );
                return {
                  ...m,
                  streamedText: newText,
                  citationsRevealed: revealed,
                  phase: "streaming",
                  citations: pendingCitations,
                };
              })
            );
          }

          if (ev.type === "done") {
            // done event from mock — timing + usedChunkIds
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiMsgId
                  ? {
                      ...m,
                      timing: ev.timing,
                      usedChunkIds: ev.usedChunkIds,
                    }
                  : m
              )
            );
          }

          if (ev.type === "error") {
            setPhase("done");
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiMsgId
                  ? { ...m, phase: "done", error: ev.error ?? "Unknown error", text: "", citations: [] }
                  : m
              )
            );
          }
        },
        ctrl.signal
      );

      setPhase("done");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiMsgId
            ? {
                ...m,
                phase: "done",
                text: m.streamedText ?? "",
                citations: pendingCitations,
                citationsRevealed: pendingCitations.length,
                elapsedMs: performance.now() - startedAt,
              }
            : m
        )
      );
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      const errMsg = err instanceof Error ? err.message : "Błąd połączenia";
      setPhase("done");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiMsgId
            ? { ...m, phase: "done", error: errMsg, text: "", citations: [] }
            : m
        )
      );
    }
  }, [activeConversationId]);

  const regenerate = useCallback(async (projectId: string, ragMode?: string) => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    await send(lastUser.text, projectId, ragMode, true);
  }, [messages, send]);

  return {
    messages,
    phase,
    isGenerating,
    activeConversationId,
    send,
    regenerate,
    lastQuery,
    stop,
    reset,
    loadHistory,
    totalMessages,
  };
}

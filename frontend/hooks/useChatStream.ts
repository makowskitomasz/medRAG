"use client";
import { useState, useRef, useCallback } from "react";
import { streamQuery, Citation, ScannedDoc, ConversationMessage } from "@/lib/api";

export type Phase = "idle" | "searching" | "thinking" | "streaming" | "done";

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
  send: (text: string, projectId: string, ragMode?: string) => Promise<void>;
  stop: () => void;
  reset: () => void;
  loadHistory: (convId: string, ragMode: string, msgs: ConversationMessage[]) => void;
}

export function useChatStream(): UseChatStreamReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
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
  }, []);

  const loadHistory = useCallback((convId: string, ragMode: string, msgs: ConversationMessage[]) => {
    abortRef.current?.abort();
    setActiveConversationId(convId);
    setPhase("idle");
    setMessages(
      msgs.map((m, i) => ({
        id: `hist-${i}`,
        role: m.role === "user" ? "user" : "ai",
        text: m.content,
        ragMode: m.role !== "user" ? ragMode : undefined,
        phase: "done" as Phase,
        citations: m.citations ?? [],
        citationsRevealed: m.citations?.length ?? 0,
      }))
    );
  }, []);

  const send = useCallback(async (text: string, projectId: string, ragMode?: string) => {
    if (!text.trim() || !projectId) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const userMsgId = `u-${Date.now()}`;
    const aiMsgId = `a-${Date.now()}`;
    aiMsgIdRef.current = aiMsgId;

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", text },
      {
        id: aiMsgId,
        role: "ai",
        text: "",
        ragMode: ragMode,
        phase: "searching",
        streamedText: "",
        citationsRevealed: 0,
        citations: [],
        thinkSteps: [],
        searchDocs: [],
        searchProgress: 0,
      },
    ]);
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
                let revealed = m.citationsRevealed ?? 0;
                // The model cites as [SOURCE_n] / 【SOURCE_n】; MessageAnswer rewrites
                // those to [n] for display, so match every form here. Scan the whole
                // text, not just this token — a marker can straddle two chunks.
                for (const r of newText.matchAll(/[[【]\s*(?:SOURCE_)?(\d+)[^\]】]*[\]】]/g)) {
                  const n = parseInt(r[1], 10);
                  if (n > revealed) revealed = n;
                }
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

  return { messages, phase, isGenerating, activeConversationId, send, stop, reset, loadHistory };
}

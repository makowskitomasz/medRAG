"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Activity, Shield, RefreshCw,
  ChevronDown, ArrowUp, Square,
  Zap, Brain, Sparkles, Users, ShieldCheck, GitMerge, AlertTriangle, Shuffle, MessageSquare,
} from "lucide-react";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import SearchingState from "@/components/chat/SearchingState";
import ThinkPanel from "@/components/chat/ThinkPanel";
import MultiAgentPanel from "@/components/chat/MultiAgentPanel";
import MessageAnswer from "@/components/chat/MessageAnswer";
import ModeSelector from "@/components/chat/ModeSelector";
import { CitationsCards, CitationsSidebar, CitationsInline } from "@/components/chat/Citations";
import { useChatStream, ChatMessage, Phase, ThinkStep } from "@/hooks/useChatStream";
import { useUIStore } from "@/store";
import { useProjects } from "@/hooks/useProjects";
import { useTranslations } from "next-intl";
import { useQueryClient } from "@tanstack/react-query";
import { conversations } from "@/lib/api";
import { getUser } from "@/lib/auth";

const MODE_ICONS: Record<string, React.ComponentType<{ size: number }>> = {
  vanilla: Zap,
  hyde: Sparkles,
  query_rewriting: RefreshCw,
  self_reflection: Brain,
  multi_agent: Users,
  corrective_rag: ShieldCheck,
  iterative_multihop: GitMerge,
  madam_rag: AlertTriangle,
  rare_rag: Shuffle,
};

const MODE_LABELS: Record<string, string> = {
  vanilla: "Vanilla",
  hyde: "HyDE",
  query_rewriting: "Rewriting",
  self_reflection: "Reflect",
  multi_agent: "Multi",
  corrective_rag: "CRAG",
  iterative_multihop: "MultiHop",
  madam_rag: "MADAM",
  rare_rag: "RARE",
};

const FOLLOW_UPS = [
  "Jakie są skutki uboczne?",
  "Ile razy dziennie przyjmować?",
  "Czy można łączyć z alkoholem?",
];

const DISCLAIMER_KEY = "medrag_disclaimer_hidden";

function useDisclaimer() {
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const hidden = localStorage.getItem(DISCLAIMER_KEY);
    if (hidden) {
      const ts = parseInt(hidden, 10);
      if (Date.now() - ts < 30 * 24 * 60 * 60 * 1000) setVisible(false);
    }
  }, []);
  const hide = () => {
    localStorage.setItem(DISCLAIMER_KEY, Date.now().toString());
    setVisible(false);
  };
  return { visible, hide };
}

export default function ChatPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const t = useTranslations("chat");
  const { citationLayout, activeProjectId, ragMode } = useUIStore();
  const { data: projectList = [], isLoading: projectsLoading } = useProjects();
  const queryClient = useQueryClient();
  const { messages, phase, isGenerating, send, stop, reset, loadHistory } = useChatStream();
  const { visible: disclaimerVisible } = useDisclaimer();

  const [input, setInput] = useState("");
  const [focusedCiteId, setFocusedCiteId] = useState<string | null>(null);
  const toggleCite = (id: string) => setFocusedCiteId((prev) => prev === id ? null : id);
  const [thinkOpen, setThinkOpen] = useState(true);
  const [citesOpen, setCitesOpen] = useState(true);
  const [convOwnerId, setConvOwnerId] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const currentUser = getUser<{ id?: string; role?: string }>();
  const activeProject = projectList.find((p) => p.project_id === activeProjectId) ?? projectList[0];

  // true when viewing another user's conversation (admin read-only mode)
  const isReadOnly = convOwnerId !== null && convOwnerId !== currentUser?.id;

  const lastAi = messages.findLast((m) => m.role === "ai");
  const convTitle = messages.find((m) => m.role === "user")?.text;

  // load conversation history when navigating to an existing chat
  useEffect(() => {
    if (!id || id === "session") return;
    conversations.get(id).then((conv) => {
      setConvOwnerId(conv.user_id ?? null);
      loadHistory(conv.id, conv.rag_mode, conv.messages);
    }).catch(() => {/* conversation not found, stay empty */});
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, lastAi?.streamedText]);

  // auto-collapse thinking panel when done
  useEffect(() => {
    if (phase === "done") {
      setThinkOpen(false);
      setCitesOpen(false);
    } else if (phase === "searching" || phase === "thinking") {
      setThinkOpen(true);
      setCitesOpen(true);
    }
  }, [phase]);

  // auto-grow textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [input]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || isGenerating || projectsLoading) return;
    if (!activeProject?.project_id) { alert("Please select a project in the sidebar."); return; }
    const text = input;
    setInput("");
    await send(text, activeProject.project_id, ragMode);
    queryClient.invalidateQueries({ queryKey: ["conversations", activeProject.project_id] });
  }, [input, isGenerating, projectsLoading, activeProject, send, queryClient, ragMode]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "n") {
        e.preventDefault();
        reset();
        router.push("/chat/new");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [reset, router]);

  return (
    <div className={`chat-root${useUIStore.getState().sidebarCollapsed ? " sidebar-collapsed" : ""}`}>
      <Sidebar
        onNewChat={() => { reset(); router.push("/chat/new"); }}
        activeConvTitle={convTitle}
      />

      <main className="chat-main">
        <TopBar project={activeProject} convTitle={convTitle} />

        <div className={`chat-body${citationLayout === "sidebar" ? " cite-sidebar" : ""}`}>
          <div className="chat-thread-wrap">
            {/* Thread */}
            <div className="chat-thread">
              <div className="chat-thread-inner">
                {/* Disclaimer */}
                {disclaimerVisible && (
                  <div className="chat-disclaimer">
                    <Shield size={14} />
                    <span>
                      {t("disclaimerPre")}{" "}
                      <strong>{t("disclaimerBold")}</strong>
                      {t("disclaimerPost")}
                    </span>
                  </div>
                )}

                {/* Empty state */}
                {messages.length === 0 && !projectsLoading && (
                  <div className="chat-empty">
                    <div className="chat-empty-icon"><MessageSquare size={48} /></div>
                    <h3>{t("emptyTitle")}</h3>
                    <p>
                      {activeProject
                        ? t("emptyDesc", { project: activeProject.name })
                        : projectList.length === 0
                        ? t("noProjectAccess")
                        : t("emptyNoProject")}
                    </p>
                  </div>
                )}

                {/* Messages */}
                {messages.map((msg) => (
                  <div key={msg.id} className={`msg ${msg.role === "user" ? "msg-user" : ""} fade-up`}>
                    {msg.role === "user" ? (
                      <>
                        <div className="msg-bubble"><p>{msg.text}</p></div>
                        <div className="msg-meta">
                          <span>{new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</span>
                        </div>
                      </>
                    ) : (
                      <AiMessage
                        msg={msg}
                        phase={phase}
                        thinkOpen={thinkOpen}
                        setThinkOpen={setThinkOpen}
                        citesOpen={citesOpen}
                        setCitesOpen={setCitesOpen}
                        focusedCiteId={focusedCiteId}
                        setFocusedCiteId={setFocusedCiteId}
                        toggleCite={toggleCite}
                        citationLayout={citationLayout}
                        isLast={msg.id === messages.findLast((m) => m.role === "ai")?.id}
                      />
                    )}
                  </div>
                ))}

                <div ref={bottomRef} />
              </div>
            </div>

            {/* Composer / Read-only / No-access banner */}
            {isReadOnly || (!projectsLoading && projectList.length === 0) ? (
              <div className="chat-readonly-banner">
                <Shield size={14} />
                <span>
                  {isReadOnly
                    ? "Read-only — this conversation belongs to another user."
                    : t("noProjectAccess")}
                </span>
              </div>
            ) : (
              <div className="chat-composer-wrap">
                <div className="chat-composer-wrap-inner">
                  <ModeSelector />
                  <div className="chat-composer">
                    <textarea
                      ref={textareaRef}
                      className="chat-input"
                      placeholder={
                        isGenerating
                          ? t("aiGenerating")
                          : activeProject
                          ? t("emptyDesc", { project: activeProject.name })
                          : t("emptyNoProject")
                      }
                      rows={1}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      disabled={isGenerating}
                    />
                    <div className="chat-composer-foot" style={{ justifyContent: "flex-end" }}>
                      <div className="chat-composer-send-wrap">
                        <span className="chat-composer-hint">
                          {isGenerating ? (
                            <span className="chat-composer-hint-live">
                              <span className="msg-live-dot" /> {t("generating")}
                            </span>
                          ) : (
                            <><kbd>⏎</kbd> {t("sendHint")} · <kbd>⇧⏎</kbd> {t("newLineHint")}</>
                          )}
                        </span>
                        {isGenerating ? (
                          <button className="chat-composer-send chat-composer-stop" onClick={stop} title="Zatrzymaj">
                            <Square size={12} />
                          </button>
                        ) : (
                          <button
                            className="chat-composer-send"
                            onClick={handleSend}
                            title="Wyślij"
                            disabled={!input.trim() || !activeProject?.project_id || projectsLoading}
                          >
                            <ArrowUp size={16} />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right sidebar citations */}
          {citationLayout === "sidebar" && lastAi && (
            <CitationsSidebar
              citations={lastAi.citations ?? []}
              revealed={phase === "done" ? (lastAi.citations?.length ?? 0) : (lastAi.citationsRevealed ?? 0)}
              focused={focusedCiteId}
              onFocus={toggleCite}
              isLoading={phase === "searching"}
            />
          )}
        </div>
      </main>
    </div>
  );
}

interface AiMsgProps {
  msg: ChatMessage;
  phase: Phase;
  thinkOpen: boolean;
  setThinkOpen: (v: boolean) => void;
  citesOpen: boolean;
  setCitesOpen: (v: boolean) => void;
  focusedCiteId: string | null;
  setFocusedCiteId: (id: string | null) => void;
  toggleCite: (id: string) => void;
  citationLayout: string;
  isLast: boolean;
}

function AiMessage({
  msg, phase, thinkOpen, setThinkOpen, citesOpen, setCitesOpen,
  focusedCiteId, setFocusedCiteId, toggleCite, citationLayout, isLast,
}: AiMsgProps) {
  const t = useTranslations("chat");
  const msgPhase = isLast ? phase : "done";
  const isGenerating = msgPhase === "searching" || msgPhase === "thinking" || msgPhase === "streaming";
  const showAnswer = msgPhase === "streaming" || msgPhase === "done" || msgPhase === "idle";
  const displayText = msgPhase === "streaming" ? (msg.streamedText ?? "") : (msg.text ?? msg.streamedText ?? "");
  const citations = msg.citations ?? [];
  const revealed = msgPhase === "done" ? citations.length : (msg.citationsRevealed ?? 0);
  const ModeIcon = MODE_ICONS[msg.ragMode ?? "vanilla"] ?? Zap;

  return (
    <div className="msg-ai">
      <div className="msg-avatar"><Activity size={18} /></div>
      <div className="msg-content">
        {/* Head */}
        <div className="msg-head">
          <span className="msg-name">medRAG</span>
          <span className="msg-mode-pill">
            <ModeIcon size={11} />
            {MODE_LABELS[msg.ragMode ?? "vanilla"] ?? msg.ragMode ?? "Vanilla"}
          </span>
          <span className="msg-time">
            {msgPhase === "searching" && <><span className="msg-live-dot" /> {t("searching")}</>}
            {msgPhase === "thinking"  && <><span className="msg-live-dot" /> {t("thinking")}</>}
            {msgPhase === "streaming" && <><span className="msg-live-dot" /> {t("streaming")}</>}
            {!isGenerating && !isLast && "5.4s"}
            {!isGenerating && isLast && msgPhase === "done" && t("done")}
          </span>
        </div>

        {/* Error */}
        {msg.error && (
          <div style={{ padding: "12px 14px", background: "rgba(239,68,68,0.1)", borderRadius: "var(--r-md)", fontSize: 14, color: "#EF4444" }}>
            {msg.error}
          </div>
        )}

        {/* Searching — show during search and stay collapsed after done (not for history msgs) */}
        {!msg.id.startsWith("hist-") && (msgPhase === "searching" || msgPhase === "streaming" || msgPhase === "done") && (
          <SearchingState
            docs={msg.searchDocs ?? []}
            progress={msg.searchProgress ?? 0}
            done={msgPhase !== "searching"}
          />
        )}

        {/* Thinking panel — ReflectPanel or MultiAgentPanel depending on mode */}
        {(msgPhase === "thinking" || (msgPhase !== "idle" && (msg.thinkSteps?.length ?? 0) > 0)) && (
          msg.ragMode === "multi_agent"
            ? <MultiAgentPanel
                steps={msg.thinkSteps ?? []}
                live={msgPhase === "thinking"}
                expanded={thinkOpen}
                onToggle={() => setThinkOpen(!thinkOpen)}
              />
            : <ThinkPanel
                steps={msg.thinkSteps ?? []}
                live={msgPhase === "thinking"}
                expanded={thinkOpen}
                onToggle={() => setThinkOpen(!thinkOpen)}
                ragMode={msg.ragMode ?? "vanilla"}
              />
        )}

        {/* Answer */}
        {showAnswer && displayText && (
          <MessageAnswer
            text={displayText}
            citations={citations}
            focusedId={focusedCiteId}
            onCiteClick={toggleCite}
            streaming={msgPhase === "streaming"}
          />
        )}

        {/* Citations — cards or inline */}
        {showAnswer && citationLayout !== "sidebar" && citations.length > 0 && (
          citationLayout === "cards" ? (
            <CitationsCards
              citations={citations}
              revealed={revealed}
              focused={focusedCiteId}
              onFocus={toggleCite}
            />
          ) : (
            <CitationsInline
              citations={citations}
              revealed={revealed}
              focused={focusedCiteId}
              onFocus={toggleCite}
            />
          )
        )}

        {/* Actions */}
        {msgPhase === "done" && !msg.error && (
          <div className="msg-actions fade-up">
            <span className="msg-cost">{t("chunksUsed", { n: citations.length })}</span>
          </div>
        )}
      </div>
    </div>
  );
}

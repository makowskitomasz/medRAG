"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Activity, Shield, RefreshCw, X,
  ArrowUp, Square, Copy, Check, RotateCw, AlertTriangle as AlertIcon,
  Zap, Brain, Sparkles, Users, ShieldCheck, GitMerge, AlertTriangle, Shuffle, MessageSquare,
  FileWarning, ChevronUp,
} from "lucide-react";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import SettingsDrawer from "@/components/layout/SettingsDrawer";
import SearchingState from "@/components/chat/SearchingState";
import ThinkPanel from "@/components/chat/ThinkPanel";
import MultiAgentPanel from "@/components/chat/MultiAgentPanel";
import MessageAnswer from "@/components/chat/MessageAnswer";
import ModeSelector from "@/components/chat/ModeSelector";
import AnswerMetrics from "@/components/chat/AnswerMetrics";
import { CitationsCards, CitationsSidebar, CitationsInline } from "@/components/chat/Citations";
import { useChatStream, ChatMessage, Phase } from "@/hooks/useChatStream";
import { useUIStore } from "@/store";
import { useProjects, useProjectDocCounts } from "@/hooks/useProjects";
import { useTranslations, useLocale } from "next-intl";
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

const DISCLAIMER_KEY = "medrag_disclaimer_hidden";
/** How many of the newest messages a long conversation opens with. */
const INITIAL_MESSAGE_WINDOW = 20;

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
  const locale = useLocale();
  // Subscribed individually — reading these off `getState()` meant the layout
  // never re-rendered when the sidebar collapsed.
  const citationLayout = useUIStore((s) => s.citationLayout);
  const activeProjectId = useUIStore((s) => s.activeProjectId);
  const ragMode = useUIStore((s) => s.ragMode);
  const sidebarCollapsed = useUIStore((s) => s.sidebarCollapsed);

  const { data: projectList = [], isLoading: projectsLoading } = useProjects();
  const docCounts = useProjectDocCounts(projectList);
  const queryClient = useQueryClient();
  const {
    messages, phase, isGenerating, send, regenerate, stop, reset, loadHistory,
    totalMessages, activeConversationId,
  } = useChatStream();
  const { visible: disclaimerVisible, hide: hideDisclaimer } = useDisclaimer();

  const [input, setInput] = useState("");
  const [focusedCiteId, setFocusedCiteId] = useState<string | null>(null);
  const toggleCite = (id: string) => setFocusedCiteId((prev) => prev === id ? null : id);
  // Panel expansion is per message — a single shared flag toggled every message
  // in the conversation at once. Missing entry = use the phase-based default.
  const [thinkOpenIds, setThinkOpenIds] = useState<Record<string, boolean>>({});
  const [citesOpenIds, setCitesOpenIds] = useState<Record<string, boolean>>({});
  const [convOwnerId, setConvOwnerId] = useState<string | null>(null);
  const [convTitleOverride, setConvTitleOverride] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [windowed, setWindowed] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const currentUser = getUser<{ id?: string; role?: string }>();
  const activeProject = projectList.find((p) => p.project_id === activeProjectId) ?? projectList[0];
  const activeDocCount = activeProject ? docCounts[activeProject.project_id] : undefined;
  const projectIsEmpty = activeDocCount === 0;
  // Starter questions are a property of the corpus, so they come from project
  // settings; a project with none simply shows no suggestions.
  const sampleQuestions = activeProject?.settings?.sample_questions ?? [];

  const isReadOnly = convOwnerId !== null && convOwnerId !== currentUser?.id;

  const lastAi = messages.findLast((m) => m.role === "ai");
  const firstQuestion = messages.find((m) => m.role === "user")?.text;
  const convTitle = convTitleOverride ?? firstQuestion;

  const conversationId = activeConversationId ?? (id !== "session" ? id : null);

  // load conversation history when navigating to an existing chat
  const fetchConversation = useCallback((convId: string, limit: number) => {
    conversations.get(convId, limit).then((conv) => {
      setConvOwnerId(conv.user_id ?? null);
      setConvTitleOverride(conv.title ?? null);
      setWindowed(conv.total_messages > conv.messages.length);
      loadHistory(conv.id, conv.rag_mode, conv.messages, {
        totalMessages: conv.total_messages,
      });
    }).catch(() => {/* conversation not found, stay empty */});
  }, [loadHistory]);

  useEffect(() => {
    if (!id || id === "session") return;
    // Long threads open on the tail; the rest is fetched only if asked for.
    fetchConversation(id, INITIAL_MESSAGE_WINDOW);
  }, [id, fetchConversation]);

  // auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, lastAi?.streamedText]);

  // auto-grow textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [input]);

  const runQuery = useCallback(async (text: string) => {
    if (!text.trim() || isGenerating || projectsLoading) return;
    if (!activeProject?.project_id) return;
    setInput("");
    try {
      await send(text, activeProject.project_id, ragMode);
    } finally {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    }
  }, [isGenerating, projectsLoading, activeProject, send, queryClient, ragMode]);

  const handleSend = useCallback(() => runQuery(input), [runQuery, input]);

  const handleRegenerate = useCallback(async () => {
    if (!activeProject?.project_id || isGenerating) return;
    await regenerate(activeProject.project_id, ragMode);
    queryClient.invalidateQueries({ queryKey: ["conversations"] });
  }, [activeProject, isGenerating, regenerate, ragMode, queryClient]);

  /** Put a failed question back in the composer so it need not be retyped. */
  const handleRetry = useCallback((question: string) => {
    setInput(question);
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

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

  const composerDisabled = !activeProject?.project_id || projectsLoading;
  const noProjects = !projectsLoading && projectList.length === 0;

  return (
    <div className={`chat-root${sidebarCollapsed ? " sidebar-collapsed" : ""}`}>
      <Sidebar
        onNewChat={() => { reset(); setConvTitleOverride(null); router.push("/chat/new"); }}
        activeConvTitle={convTitle}
        activeConvId={conversationId ?? undefined}
        mobileOpen={mobileNavOpen}
        onMobileClose={() => setMobileNavOpen(false)}
        onSettingsOpen={() => setSettingsOpen(true)}
      />

      <main className="chat-main">
        <TopBar
          project={activeProject}
          convTitle={convTitle}
          onSettingsOpen={() => setSettingsOpen(true)}
          onMenuOpen={() => setMobileNavOpen(true)}
        />

        <div className={`chat-body${citationLayout === "sidebar" ? " cite-sidebar" : ""}`}>
          <div className="chat-thread-wrap">
            {/* Thread */}
            <div className="chat-thread">
              <div className="chat-thread-inner">
                {/* Disclaimer */}
                {disclaimerVisible && (
                  <div className="chat-disclaimer">
                    <Shield size={14} aria-hidden="true" />
                    <span>
                      {t("disclaimerPre")}{" "}
                      <strong>{t("disclaimerBold")}</strong>
                      {t("disclaimerPost")}
                    </span>
                    <button
                      className="icon-btn chat-disclaimer-x"
                      onClick={hideDisclaimer}
                      aria-label={t("disclaimerDismiss")}
                      title={t("disclaimerDismiss")}
                    >
                      <X size={13} />
                    </button>
                  </div>
                )}

                {/* Project has no indexed documents — every answer would be a refusal */}
                {projectIsEmpty && !noProjects && (
                  <div className="chat-empty-project">
                    <FileWarning size={16} aria-hidden="true" />
                    <div>
                      <strong>{t("emptyProjectTitle")}</strong>
                      <p>{t("emptyProjectDesc")}</p>
                    </div>
                    {currentUser?.role === "admin" && (
                      <button className="btn-ghost" onClick={() => router.push("/admin")}>
                        {t("emptyProjectAdminHint")}
                      </button>
                    )}
                  </div>
                )}

                {/* Older messages exist beyond the initial window */}
                {windowed && (
                  <button
                    className="chat-load-earlier"
                    onClick={() => { setWindowed(false); fetchConversation(id, 0); }}
                  >
                    <ChevronUp size={13} aria-hidden="true" />
                    {t("loadEarlier")}
                    <span className="chat-load-earlier-sub">
                      {t("showingLastN", { n: messages.length, total: totalMessages })}
                    </span>
                  </button>
                )}

                {/* Empty state */}
                {messages.length === 0 && !projectsLoading && (
                  <div className="chat-empty">
                    <div className="chat-empty-icon"><MessageSquare size={48} aria-hidden="true" /></div>
                    <h3>{t("emptyTitle")}</h3>
                    <p>
                      {activeProject
                        ? t("emptyDesc", { project: activeProject.name })
                        : projectList.length === 0
                        ? t("noProjectAccess")
                        : t("emptyNoProject")}
                    </p>
                    {!projectIsEmpty && sampleQuestions.length > 0 && (
                      <div className="chat-suggestions">
                        <span className="chat-suggestions-h">{t("suggestedTitle")}</span>
                        {sampleQuestions.map((q) => (
                          <button key={q} className="chat-suggestion" onClick={() => runQuery(q)}>
                            {q}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Messages */}
                <div aria-live="polite" aria-atomic="false" aria-relevant="additions text">
                  {messages.map((msg, i) => (
                    <div key={msg.id} className={`msg ${msg.role === "user" ? "msg-user" : ""} fade-up`}>
                      {msg.role === "user" ? (
                        <>
                          <div className="msg-bubble"><p>{msg.text}</p></div>
                          {msg.createdAt != null && (
                            <div className="msg-meta">
                              <span>
                                {new Date(msg.createdAt).toLocaleTimeString(locale, {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </span>
                            </div>
                          )}
                        </>
                      ) : (
                        <AiMessage
                          msg={msg}
                          phase={phase}
                          thinkOpen={thinkOpenIds[msg.id]}
                          setThinkOpen={(v) => setThinkOpenIds((prev) => ({ ...prev, [msg.id]: v }))}
                          citesOpen={citesOpenIds[msg.id]}
                          setCitesOpen={(v) => setCitesOpenIds((prev) => ({ ...prev, [msg.id]: v }))}
                          focusedCiteId={focusedCiteId}
                          setFocusedCiteId={setFocusedCiteId}
                          toggleCite={toggleCite}
                          citationLayout={citationLayout}
                          isLast={msg.id === messages.findLast((m) => m.role === "ai")?.id}
                          onRegenerate={handleRegenerate}
                          onRetry={() => handleRetry(messages[i - 1]?.text ?? "")}
                          canAct={!isReadOnly && !composerDisabled}
                        />
                      )}
                    </div>
                  ))}
                </div>

                <div ref={bottomRef} />
              </div>
            </div>

            {/* Composer / Read-only / No-access banner */}
            {isReadOnly || noProjects ? (
              <div className="chat-readonly-banner">
                <Shield size={14} aria-hidden="true" />
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
                      aria-label={t("emptyTitle")}
                      placeholder={
                        isGenerating
                          ? t("aiGenerating")
                          : !activeProject
                          ? t("emptyNoProject")
                          : projectIsEmpty
                          ? t("emptyProjectTitle")
                          : t("emptyDesc", { project: activeProject.name })
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
                          ) : composerDisabled ? (
                            t("selectProjectFirst")
                          ) : (
                            <><kbd>⏎</kbd> {t("sendHint")} · <kbd>⇧⏎</kbd> {t("newLineHint")}</>
                          )}
                        </span>
                        {isGenerating ? (
                          <button
                            className="chat-composer-send chat-composer-stop"
                            onClick={stop}
                            title={t("stop")}
                            aria-label={t("stop")}
                          >
                            <Square size={12} />
                          </button>
                        ) : (
                          <button
                            className="chat-composer-send"
                            onClick={handleSend}
                            title={t("send")}
                            aria-label={t("send")}
                            disabled={!input.trim() || composerDisabled}
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

      <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}

interface AiMsgProps {
  msg: ChatMessage;
  phase: Phase;
  /** undefined = not toggled by the user yet, fall back to the phase default. */
  thinkOpen: boolean | undefined;
  setThinkOpen: (v: boolean) => void;
  citesOpen: boolean | undefined;
  setCitesOpen: (v: boolean) => void;
  focusedCiteId: string | null;
  setFocusedCiteId: (id: string | null) => void;
  toggleCite: (id: string) => void;
  citationLayout: string;
  isLast: boolean;
  onRegenerate: () => void;
  onRetry: () => void;
  canAct: boolean;
}

function AiMessage({
  msg, phase, thinkOpen, setThinkOpen,
  focusedCiteId, toggleCite, citationLayout, isLast,
  onRegenerate, onRetry, canAct,
}: AiMsgProps) {
  const t = useTranslations("chat");
  const [copied, setCopied] = useState(false);
  const msgPhase = isLast ? phase : "done";
  const isGenerating = msgPhase === "searching" || msgPhase === "thinking" || msgPhase === "streaming";
  const showAnswer = msgPhase === "streaming" || msgPhase === "done" || msgPhase === "idle";
  const displayText = msgPhase === "streaming" ? (msg.streamedText ?? "") : (msg.text ?? msg.streamedText ?? "");
  const citations = msg.citations ?? [];
  const revealed = msgPhase === "done" ? citations.length : (msg.citationsRevealed ?? 0);
  const ModeIcon = MODE_ICONS[msg.ragMode ?? "vanilla"] ?? Zap;
  // Expanded while this message is still being produced, collapsed once finished —
  // unless the user has explicitly toggled this particular message.
  const thinkExpanded = thinkOpen ?? isGenerating;

  const copyAnswer = () => {
    navigator.clipboard.writeText(displayText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }).catch(() => {});
  };

  return (
    <div className="msg-ai">
      <div className="msg-avatar" aria-hidden="true"><Activity size={18} /></div>
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
            {!isGenerating && !isLast && msg.elapsedMs != null && `${(msg.elapsedMs / 1000).toFixed(1)}s`}
            {!isGenerating && isLast && msgPhase === "done" && (
              msg.elapsedMs != null ? `${t("done")} · ${(msg.elapsedMs / 1000).toFixed(1)}s` : t("done")
            )}
          </span>
        </div>

        {/* Error */}
        {msg.error && (
          <div className="msg-error" role="alert">
            <AlertIcon size={14} aria-hidden="true" />
            <span>{msg.error}</span>
            {canAct && (
              <button className="btn-ghost msg-error-retry" onClick={onRetry}>
                <RotateCw size={12} /> {t("retryQuestion")}
              </button>
            )}
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
          msg.ragMode === "multi_agent" || msg.ragMode === "madam_rag"
            ? <MultiAgentPanel
                steps={msg.thinkSteps ?? []}
                live={msgPhase === "thinking"}
                expanded={thinkExpanded}
                onToggle={() => setThinkOpen(!thinkExpanded)}
                ragMode={msg.ragMode}
              />
            : <ThinkPanel
                steps={msg.thinkSteps ?? []}
                live={msgPhase === "thinking"}
                expanded={thinkExpanded}
                onToggle={() => setThinkOpen(!thinkExpanded)}
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
          <>
            <AnswerMetrics elapsedMs={msg.elapsedMs} inputTokens={msg.inputTokens} outputTokens={msg.outputTokens} />
            <div className="msg-actions fade-up">
              <span className="msg-cost">{t("chunksUsed", { n: citations.length })}</span>
              {displayText && (
                <button className="btn-ghost msg-action" onClick={copyAnswer} title={t("copyAnswer")}>
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                  {copied ? t("copied") : t("copy")}
                </button>
              )}
              {isLast && canAct && (
                <button className="btn-ghost msg-action" onClick={onRegenerate} title={t("regenerate")}>
                  <RotateCw size={12} /> {t("regenerate")}
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

"use client";
export const dynamic = "force-dynamic";
import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ChevronRight, Play, Square, AlertTriangle } from "lucide-react";
import MessageAnswer from "@/components/chat/MessageAnswer";
import { CitationsCards } from "@/components/chat/Citations";
import { useProjects } from "@/hooks/useProjects";
import { useUIStore } from "@/store";
import { streamQuery, Citation } from "@/lib/api";

const MODES = [
  "vanilla", "hyde", "query_rewriting", "self_reflection", "multi_agent",
  "corrective_rag", "iterative_multihop", "madam_rag", "rare_rag",
] as const;

const MODE_LABELS: Record<string, string> = {
  vanilla: "Vanilla",
  hyde: "HyDE",
  query_rewriting: "Rewriting",
  self_reflection: "Reflect",
  multi_agent: "Multi-Agent",
  corrective_rag: "CRAG",
  iterative_multihop: "MultiHop",
  madam_rag: "MADAM",
  rare_rag: "RARE",
};

interface RunState {
  text: string;
  citations: Citation[];
  elapsedMs: number | null;
  running: boolean;
  error: string | null;
  steps: string[];
}

const EMPTY: RunState = {
  text: "", citations: [], elapsedMs: null, running: false, error: null, steps: [],
};

/**
 * Runs one question through two architectures at once. `rag_mode_override` already
 * existed per request, so the comparison the thesis is about needed no backend work
 * beyond what the chat view uses.
 */
export default function ComparePage() {
  const router = useRouter();
  const t = useTranslations("compare");
  const { activeProjectId, setActiveProjectId } = useUIStore();
  const { data: projectList = [] } = useProjects();

  const [question, setQuestion] = useState("");
  const [modeA, setModeA] = useState<string>("vanilla");
  const [modeB, setModeB] = useState<string>("rare_rag");
  const [runA, setRunA] = useState<RunState>(EMPTY);
  const [runB, setRunB] = useState<RunState>(EMPTY);
  const abortRef = useRef<AbortController | null>(null);

  const projectId = activeProjectId ?? projectList[0]?.project_id ?? null;
  const busy = runA.running || runB.running;

  const runOne = useCallback(async (
    mode: string,
    setState: React.Dispatch<React.SetStateAction<RunState>>,
    signal: AbortSignal,
  ) => {
    setState({ ...EMPTY, running: true });
    const startedAt = performance.now();
    const citations: Citation[] = [];
    try {
      await streamQuery(
        // A fresh conversation per run keeps the two pipelines from sharing history.
        { project_id: projectId!, query: question, conversation_id: null, rag_mode_override: mode },
        (ev) => {
          if (ev.type === "token") {
            const token = ev.text ?? ev.content ?? "";
            setState((s) => ({ ...s, text: s.text + token }));
          } else if (ev.type === "think" && ev.label) {
            setState((s) => (s.steps.includes(ev.label!) ? s : { ...s, steps: [...s.steps, ev.label!] }));
          } else if (ev.type === "citations") {
            citations.push(...(ev.citations ?? []));
            setState((s) => ({ ...s, citations: [...citations] }));
          } else if (ev.type === "error") {
            setState((s) => ({ ...s, error: ev.error ?? "Unknown error" }));
          }
        },
        signal,
      );
      setState((s) => ({ ...s, running: false, elapsedMs: performance.now() - startedAt, citations: [...citations] }));
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        setState((s) => ({ ...s, running: false }));
        return;
      }
      setState((s) => ({
        ...s,
        running: false,
        error: err instanceof Error ? err.message : "Request failed",
        elapsedMs: performance.now() - startedAt,
      }));
    }
  }, [projectId, question]);

  const run = useCallback(() => {
    if (!question.trim() || !projectId || busy) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    // Both pipelines start together so the wall times are comparable.
    void Promise.all([
      runOne(modeA, setRunA, ctrl.signal),
      runOne(modeB, setRunB, ctrl.signal),
    ]);
  }, [question, projectId, busy, runOne, modeA, modeB]);

  const stop = () => abortRef.current?.abort();

  const hasRun = runA.text || runB.text || runA.error || runB.error || busy;

  return (
    <div className="cmp-root fade-in">
      <div className="cmp-header">
        <button className="btn-ghost hist-back" onClick={() => router.push("/chat/new")}>
          <ChevronRight size={14} style={{ transform: "rotate(180deg)" }} aria-hidden="true" />
          {t("back")}
        </button>
        <h1>{t("title")}</h1>
        <p>{t("subtitle")}</p>
      </div>

      <div className="cmp-controls">
        <label className="cmp-field">
          <span>{t("project")}</span>
          <select
            value={projectId ?? ""}
            onChange={(e) => setActiveProjectId(e.target.value)}
          >
            {projectList.map((p) => (
              <option key={p.project_id} value={p.project_id}>{p.name}</option>
            ))}
          </select>
        </label>

        <label className="cmp-field cmp-field-mode">
          <span>{t("modeA")}</span>
          <select value={modeA} onChange={(e) => setModeA(e.target.value)}>
            {MODES.map((m) => <option key={m} value={m}>{MODE_LABELS[m]}</option>)}
          </select>
        </label>

        <label className="cmp-field cmp-field-mode">
          <span>{t("modeB")}</span>
          <select value={modeB} onChange={(e) => setModeB(e.target.value)}>
            {MODES.map((m) => <option key={m} value={m}>{MODE_LABELS[m]}</option>)}
          </select>
        </label>
      </div>

      {modeA === modeB && <div className="cmp-warn"><AlertTriangle size={13} /> {t("sameMode")}</div>}

      <div className="cmp-ask">
        <textarea
          className="chat-input cmp-input"
          rows={2}
          placeholder={t("placeholder")}
          aria-label={t("question")}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); run(); }
          }}
          disabled={busy}
        />
        {busy ? (
          <button className="btn btn-primary cmp-run" onClick={stop}>
            <Square size={14} /> {t("running")}
          </button>
        ) : (
          <button
            className="btn btn-primary cmp-run"
            onClick={run}
            disabled={!question.trim() || !projectId}
          >
            <Play size={14} /> {t("run")}
          </button>
        )}
      </div>

      {!hasRun ? (
        <div className="cmp-empty">{t("emptyState")}</div>
      ) : (
        <div className="cmp-grid">
          <ComparePane label={MODE_LABELS[modeA]} state={runA} />
          <ComparePane label={MODE_LABELS[modeB]} state={runB} />
        </div>
      )}
    </div>
  );
}

function ComparePane({ label, state }: { label: string; state: RunState }) {
  const t = useTranslations("compare");
  const [focused, setFocused] = useState<string | null>(null);

  return (
    <section className="cmp-pane" aria-label={label}>
      <header className="cmp-pane-head">
        <span className="cmp-pane-mode">{label}</span>
        {state.running && <span className="cmp-pane-live"><span className="msg-live-dot" /> {t("waiting")}</span>}
        <div className="cmp-pane-stats">
          {state.elapsedMs != null && (
            <span title={t("elapsed")}>{(state.elapsedMs / 1000).toFixed(1)}s</span>
          )}
          <span title={t("citations")}>{state.citations.length} ⟡</span>
          <span title={t("chars")}>{state.text.length}</span>
        </div>
      </header>

      {state.steps.length > 0 && (
        <div className="cmp-pane-steps">
          {state.steps.map((s) => <span key={s} className="cmp-step">{s}</span>)}
        </div>
      )}

      <div className="cmp-pane-body" aria-live="polite">
        {state.error ? (
          <div className="msg-error" role="alert">
            <AlertTriangle size={14} aria-hidden="true" /> {state.error}
          </div>
        ) : state.text ? (
          <>
            <MessageAnswer
              text={state.text}
              citations={state.citations}
              focusedId={focused}
              onCiteClick={(id) => setFocused((p) => (p === id ? null : id))}
              streaming={state.running}
            />
            {state.citations.length > 0 && (
              <CitationsCards
                citations={state.citations}
                revealed={state.citations.length}
                focused={focused}
                onFocus={(id) => setFocused((p) => (p === id ? null : id))}
              />
            )}
          </>
        ) : state.running ? (
          <div className="cmp-pane-skeleton">
            <span /><span /><span />
          </div>
        ) : (
          <p className="cmp-pane-none">{t("noAnswer")}</p>
        )}
      </div>
    </section>
  );
}

"use client";
import { Layers, ChevronDown, Check, Quote } from "lucide-react";
import { ThinkStep } from "@/hooks/useChatStream";

interface Props {
  steps: ThinkStep[];
  live: boolean;
  expanded: boolean;
  onToggle: () => void;
  ragMode?: string;
}

interface AgentMeta {
  name: string;
  color: string;
  desc: string;
}

/**
 * Agent keys are sent by the orchestrator (`agent` field on `think` events).
 * multi_agent → researcher/critic/editor, madam_rag → advocate/skeptic/arbiter.
 */
const AGENTS: Record<string, AgentMeta> = {
  researcher: { name: "Researcher", color: "#7DD3FC", desc: "Mechanism of action and pharmacokinetics" },
  critic:     { name: "Critic",     color: "#C7CEEA", desc: "Clinical risks and adverse effects" },
  editor:     { name: "Editor",     color: "#6EE7B7", desc: "Dosing, monitoring and management" },
  advocate:   { name: "Advocate",   color: "#6EE7B7", desc: "Supporting evidence and benefits" },
  skeptic:    { name: "Skeptic",    color: "#FCA5A5", desc: "Risks and opposing evidence" },
  arbiter:    { name: "Arbiter",    color: "#FCD34D", desc: "Conflicting or uncertain evidence" },
  moderator:  { name: "Moderator",  color: "#C7CEEA", desc: "Merges the agents' findings" },
  reasoning:  { name: "Reasoning",  color: "#A5B4FC", desc: "Model chain-of-thought" },
};

const EXPECTED_AGENTS: Record<string, number> = {
  multi_agent: 4, // 3 agents + moderator
  madam_rag: 5,   // 3 debaters + conflict detection + merge
};

const PANEL_LABEL: Record<string, string> = {
  multi_agent: "Multi-Agent",
  madam_rag: "MADAM — debate",
};

function metaFor(step: ThinkStep): AgentMeta {
  if (step.agent && AGENTS[step.agent]) return AGENTS[step.agent];
  if (step.label === "Reasoning") return AGENTS.reasoning;
  // Unknown/extra step (e.g. a pipeline stage without an agent) — derive from its label.
  return { name: step.label || "Step", color: "#C7CEEA", desc: "" };
}

export default function MultiAgentPanel({ steps, live, expanded, onToggle, ragMode = "multi_agent" }: Props) {
  const totalMs = steps.reduce((s, t) => s + t.durationMs, 0);
  const totalSec = (totalMs / 1000).toFixed(1);
  const expected = EXPECTED_AGENTS[ragMode] ?? steps.length;

  const summary = live
    ? steps.length === 0
      ? "Initializing agents…"
      : `Step ${steps.length} of ${Math.max(expected, steps.length)}`
    : `${steps.length} steps · ${totalSec}s`;

  return (
    <div className={`think-panel${expanded ? " think-panel-open" : ""}${live ? " think-panel-live" : ""}`}>
      <button className="think-head" onClick={onToggle}>
        <div className="think-head-l">
          <span className="think-badge">
            <Layers size={13} />
            {PANEL_LABEL[ragMode] ?? "Multi-Agent"}
            {live && <span className="think-badge-dot" />}
          </span>
          <span className="think-summary">{summary}</span>
        </div>
        <ChevronDown size={16} className="think-chev" />
      </button>

      {expanded && (
        <div className="think-body">
          <div className="multi-agents">
            {steps.map((step, i) => {
              const agent = metaFor(step);
              const isCurrent = live && i === steps.length - 1;

              return (
                <div
                  key={`${step.step}-${i}`}
                  className={`multi-agent fade-up${isCurrent ? " multi-agent-current" : ""}`}
                >
                  <div className="multi-agent-head">
                    <span className="multi-agent-avatar" style={{ background: agent.color }}>
                      {agent.name[0]}
                    </span>
                    <div>
                      <div className="multi-agent-name">
                        {agent.name}
                        {!isCurrent && <Check size={11} className="multi-agent-check" />}
                        {step.durationMs > 0 && (
                          <span className="think-step-time" style={{ marginLeft: 8 }}>
                            {(step.durationMs / 1000).toFixed(1)}s
                          </span>
                        )}
                      </div>
                      <div className="multi-agent-desc">{agent.desc || step.label}</div>
                    </div>
                  </div>
                  <div className="multi-agent-msg">
                    <Quote size={11} />
                    <span>{step.text || "—"}</span>
                  </div>
                </div>
              );
            })}

            {/* Next agent still working */}
            {live && (
              <div className="multi-agent multi-agent-current fade-up">
                <div className="multi-agent-head">
                  <span className="multi-agent-avatar" style={{ background: "#C7CEEA" }}>
                    …
                  </span>
                  <div>
                    <div className="multi-agent-name">Working…</div>
                    <div className="multi-agent-desc">
                      {steps.length < expected ? `Step ${steps.length + 1} of ${expected}` : "Finalizing"}
                    </div>
                  </div>
                </div>
                <div className="multi-agent-msg">
                  <Quote size={11} />
                  <span className="dots-anim"><span /><span /><span /></span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

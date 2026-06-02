"use client";
import { Layers, ChevronDown, Check, Quote } from "lucide-react";
import { ThinkStep } from "@/hooks/useChatStream";

interface Props {
  steps: ThinkStep[];
  live: boolean;
  expanded: boolean;
  onToggle: () => void;
}

const AGENTS: Record<string, { name: string; color: string; desc: string }> = {
  research: { name: "Researcher", color: "#7DD3FC", desc: "Searches document fragments" },
  critic:   { name: "Critic",     color: "#C7CEEA", desc: "Checks coherence and completeness" },
  editor:   { name: "Editor",     color: "#6EE7B7", desc: "Compiles findings into a clear answer" },
};

const AGENT_ORDER = ["research", "critic", "editor"] as const;

export default function MultiAgentPanel({ steps, live, expanded, onToggle }: Props) {
  const totalMs = steps.reduce((s, t) => s + t.durationMs, 0);
  const totalSec = (totalMs / 1000).toFixed(1);

  const summary = live
    ? steps.length === 0
      ? "Initializing agents…"
      : `Agent ${steps.length} of 3`
    : `3 AI agents · ${totalSec}s`;

  // Map received steps to agents by `agent` field or by order
  const agentStepMap = new Map<string, ThinkStep>();
  for (const s of steps) {
    const agentKey = s.agent ?? AGENT_ORDER[s.step] ?? "";
    if (agentKey) agentStepMap.set(agentKey, s);
  }

  // Which agents to show: all received + (if live) one more in progress
  const visibleCount = steps.length + (live ? 1 : 0);

  return (
    <div className={`think-panel${expanded ? " think-panel-open" : ""}${live ? " think-panel-live" : ""}`}>
      <button className="think-head" onClick={onToggle}>
        <div className="think-head-l">
          <span className="think-badge">
            <Layers size={13} />
            Multi-Agent
            {live && <span className="think-badge-dot" />}
          </span>
          <span className="think-summary">{summary}</span>
        </div>
        <ChevronDown size={16} className="think-chev" />
      </button>

      {expanded && (
        <div className="think-body">
          <div className="multi-agents">
            {AGENT_ORDER.slice(0, Math.min(visibleCount, AGENT_ORDER.length)).map((agentKey, i) => {
              const agent = AGENTS[agentKey];
              const step = agentStepMap.get(agentKey) ?? steps[i];
              const isDone = !!step && i < steps.length;
              const isCurrent = live && i === steps.length;

              return (
                <div
                  key={agentKey}
                  className={`multi-agent fade-up${isCurrent ? " multi-agent-current" : ""}`}
                >
                  <div className="multi-agent-head">
                    <span
                      className="multi-agent-avatar"
                      style={{ background: agent.color }}
                    >
                      {agent.name[0]}
                    </span>
                    <div>
                      <div className="multi-agent-name">
                        {agent.name}
                        {isDone && <Check size={11} className="multi-agent-check" />}
                      </div>
                      <div className="multi-agent-desc">{agent.desc}</div>
                    </div>
                  </div>
                  <div className="multi-agent-msg">
                    <Quote size={11} />
                    {isCurrent
                      ? <span className="dots-anim"><span /><span /><span /></span>
                      : <span>{step?.text ?? "—"}</span>
                    }
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

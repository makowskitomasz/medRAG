"use client";
import { Brain, ChevronDown, Check } from "lucide-react";
import { useTranslations } from "next-intl";
import { ThinkStep } from "@/hooks/useChatStream";

interface Props {
  steps: ThinkStep[];
  totalSteps?: number;   // known total (if backend provides it), otherwise undefined
  live: boolean;
  expanded: boolean;
  onToggle: () => void;
}

export default function ThinkPanel({ steps, totalSteps, live, expanded, onToggle }: Props) {
  const tr = useTranslations("chat");
  const totalMs = steps.reduce((s, t) => s + t.durationMs, 0);
  const totalSec = (totalMs / 1000).toFixed(1);

  const summary = live
    ? steps.length === 0
      ? tr("thinking_placeholder")
      : tr("thinking_live", { n: steps.length, s: totalSec })
    : tr("thinking_done", { n: steps.length, s: totalSec });

  return (
    <div className={`think-panel${expanded ? " think-panel-open" : ""}${live ? " think-panel-live" : ""}`}>
      <button className="think-head" onClick={onToggle}>
        <div className="think-head-l">
          <span className="think-badge">
            <Brain size={13} />
            Self-Reflection
            {live && <span className="think-badge-dot" />}
          </span>
          <span className="think-summary">{summary}</span>
        </div>
        <ChevronDown size={16} className="think-chev" />
      </button>

      {expanded && (
        <div className="think-body">
          {steps.length === 0 && live ? (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0", fontSize: 13, color: "var(--text-2)" }}>
              <div className="search-spinner search-spinner-sm" />
              {tr("thinking_placeholder")}
            </div>
          ) : (
            <div className="think-timeline">
              {/* Render done steps */}
              {steps.map((s, i) => (
                <div key={i} className="think-step think-step-done">
                  <div className="think-step-dot">
                    <span className="think-step-n think-step-n-done">
                      <Check size={12} />
                    </span>
                    {(i < steps.length - 1 || live) && <span className="think-step-line" />}
                  </div>
                  <div className="think-step-body">
                    <div className="think-step-head">
                      <span className="think-step-label">{s.label}</span>
                      <span className="think-step-time">{(s.durationMs / 1000).toFixed(1)}s</span>
                    </div>
                    <p className="think-step-text">{s.text}</p>
                  </div>
                </div>
              ))}
              {/* Render "current" spinner when still live */}
              {live && (
                <div className="think-step think-step-current">
                  <div className="think-step-dot">
                    <span className="think-step-n">
                      <div className="search-spinner search-spinner-sm" />
                    </span>
                  </div>
                  <div className="think-step-body">
                    <div className="think-step-head">
                      <span className="think-step-label think-step-label-muted">{steps.length + 1}</span>
                      <span className="think-step-time think-step-time-live">running…</span>
                    </div>
                    <p className="think-step-text">
                      <span className="dots-anim"><span /><span /><span /></span>
                    </p>
                  </div>
                </div>
              )}
              {/* Pending placeholder steps (when total is known) */}
              {totalSteps && !live && totalSteps > steps.length && (
                Array.from({ length: totalSteps - steps.length }).map((_, i) => (
                  <div key={`pending-${i}`} className="think-step think-step-pending">
                    <div className="think-step-dot">
                      <span className="think-step-n think-step-n-pending">
                        {steps.length + i + 1}
                      </span>
                      {i < totalSteps - steps.length - 1 && <span className="think-step-line" />}
                    </div>
                    <div className="think-step-body">
                      <div className="think-step-head">
                        <span className="think-step-label think-step-label-muted">—</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

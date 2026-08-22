"use client";
import { useState, useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import {
  Zap, Brain, Sparkles, Users, RefreshCw, ShieldCheck,
  GitMerge, AlertTriangle, Shuffle,
} from "lucide-react";
import { useUIStore } from "@/store";

type RagModeId =
  | "vanilla" | "hyde" | "query_rewriting" | "self_reflection" | "multi_agent"
  | "corrective_rag" | "iterative_multihop" | "madam_rag" | "rare_rag";

interface ModeConfig {
  id: RagModeId;
  /** Fallback label — the rendered text comes from next-intl (`modes.*`). */
  label: string;
  Icon: React.ComponentType<{ size: number }>;
}

/**
 * Copy (label, tag, description, avg time, quality) lives in `messages/{pl,en}.json`
 * under `modes.*`. The `*_time` values are measured end-to-end wall times on the DDI
 * corpus with LLM_MODEL=openai/gpt-oss-120b; `*_quality` buckets follow the measured
 * faithfulness in results/thesis_final/ddi.csv. Re-measure after changing the model.
 */
const MODES: ModeConfig[] = [
  {
    id: "vanilla",
    label: "Vanilla",
    Icon: Zap,
  },
  {
    id: "hyde",
    label: "HyDE",
    Icon: Sparkles,
  },
  {
    id: "query_rewriting",
    label: "Rewriting",
    Icon: RefreshCw,
  },
  {
    id: "self_reflection",
    label: "Reflect",
    Icon: Brain,
  },
  {
    id: "multi_agent",
    label: "Multi",
    Icon: Users,
  },
  {
    id: "corrective_rag",
    label: "CRAG",
    Icon: ShieldCheck,
  },
  {
    id: "iterative_multihop",
    label: "MultiHop",
    Icon: GitMerge,
  },
  {
    id: "madam_rag",
    label: "MADAM",
    Icon: AlertTriangle,
  },
  {
    id: "rare_rag",
    label: "RARE",
    Icon: Shuffle,
  },
];

export const MODE_META: Record<RagModeId, { label: string; Icon: React.ComponentType<{ size: number }> }> =
  Object.fromEntries(MODES.map((m) => [m.id, { label: m.label, Icon: m.Icon }])) as Record<
    RagModeId,
    { label: string; Icon: React.ComponentType<{ size: number }> }
  >;

export default function ModeSelector() {
  const { ragMode, setRagMode } = useUIStore();
  const t = useTranslations("modes");
  const tc = useTranslations("chat");
  const [hoveredId, setHoveredId] = useState<RagModeId | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const hovered = MODES.find((m) => m.id === hoveredId);

  const handleEnter = (id: RagModeId) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setHoveredId(id), 120);
  };
  const handleLeave = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setHoveredId(null), 200);
  };
  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  return (
    <div className="mode-wrap" style={{ position: "relative", alignItems: "center", minWidth: 0 }}>
      <span className="mode-label" style={{ flexShrink: 0 }}>{tc("modeLabel")}</span>

      <div style={{ position: "relative", minWidth: 0, flex: 1 }}>
        {/* Single-row scrollable segmented control */}
        <div
          className="mode-segmented"
          style={{ display: "flex", flexWrap: "nowrap", overflowX: "auto", scrollbarWidth: "none" }}
        >
          {MODES.map(({ id, Icon }) => (
            <button
              key={id}
              className={`mode-seg${ragMode === id ? " mode-seg-active" : ""}`}
              onClick={() => setRagMode(id)}
              onMouseEnter={() => handleEnter(id)}
              onMouseLeave={handleLeave}
            >
              <Icon size={11} />
              {t(id as keyof typeof t)}
            </button>
          ))}
        </div>

        {/* Hover popover */}
        {hovered && (
          <div
            className="mode-popover"
            style={{
              position: "absolute",
              bottom: "calc(100% + 10px)",
              left: 0,
              width: 300,
              padding: 14,
              background: "var(--bg-elev)",
              border: "1px solid var(--border-strong)",
              borderRadius: "var(--r-md)",
              boxShadow: "var(--shadow-lg)",
              zIndex: 50,
            }}
            onMouseEnter={() => { if (timerRef.current) clearTimeout(timerRef.current); setHoveredId(hovered.id); }}
            onMouseLeave={handleLeave}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <div style={{
                width: 28, height: 28, borderRadius: 8,
                background: "var(--accent-soft)", color: "var(--accent)",
                display: "grid", placeItems: "center", flexShrink: 0,
              }}>
                <hovered.Icon size={14} />
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{t(hovered.id as keyof typeof t)}</div>
                <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)" }}>
                  {t(`${hovered.id}_tag` as keyof typeof t)}
                </div>
              </div>
            </div>
            <p style={{ fontSize: 12.5, lineHeight: 1.55, color: "var(--text-2)", margin: "0 0 10px" }}>
              {t(`${hovered.id}_desc` as keyof typeof t)}
            </p>
            <div style={{
              display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8,
              borderTop: "1px solid var(--border)", paddingTop: 10,
            }}>
              <div>
                <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)", marginBottom: 3 }}>
                  {t("avgTime")}
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, fontFamily: "var(--font-mono)", color: "var(--text)" }}>
                  {t(`${hovered.id}_time` as keyof typeof t)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)", marginBottom: 3 }}>
                  {t("quality")}
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, fontFamily: "var(--font-mono)", color: "var(--text)" }}>
                  {t(`${hovered.id}_quality` as keyof typeof t)}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

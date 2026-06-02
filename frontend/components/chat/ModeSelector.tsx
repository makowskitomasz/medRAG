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
  label: string;
  tag: string;
  Icon: React.ComponentType<{ size: number }>;
  desc: string;
  avgTime: string;
  quality: string;
}

const MODES: ModeConfig[] = [
  {
    id: "vanilla",
    label: "Vanilla",
    tag: "PODSTAWOWY",
    Icon: Zap,
    desc: "Bezpośrednie wyszukiwanie i generacja. Najszybszy tryb, idealny do prostych pytań.",
    avgTime: "~3s",
    quality: "Dobra",
  },
  {
    id: "hyde",
    label: "HyDE",
    tag: "ZAAWANSOWANY",
    Icon: Sparkles,
    desc: "Generuje hipotetyczną odpowiedź, by wyszukać podobne fragmenty. Lepszy przy złożonych pytaniach.",
    avgTime: "~5s",
    quality: "Lepsza",
  },
  {
    id: "query_rewriting",
    label: "Rewriting",
    tag: "KONTEKST",
    Icon: RefreshCw,
    desc: "Przepisuje pytanie uwzględniając historię rozmowy. Polecany w wieloturowych dialogach.",
    avgTime: "~4s",
    quality: "Dobra+",
  },
  {
    id: "self_reflection",
    label: "Reflect",
    tag: "ITERACYJNY",
    Icon: Brain,
    desc: "Generuje odpowiedź, ocenia jej jakość i iteruje. Wyższe koszty, wysoka precyzja.",
    avgTime: "~8s",
    quality: "Wysoka",
  },
  {
    id: "multi_agent",
    label: "Multi",
    tag: "AGENTY",
    Icon: Users,
    desc: "Trzy agenty (Badacz, Krytyk, Redaktor) współpracują. Dobry przy skomplikowanych przypadkach.",
    avgTime: "~10s",
    quality: "Wysoka",
  },
  {
    id: "corrective_rag",
    label: "CRAG",
    tag: "KOREKCJA",
    Icon: ShieldCheck,
    desc: "Filtruje słabe fragmenty i uruchamia fallback przy niskiej trafności. Odporny na zaszumione dane.",
    avgTime: "~5s",
    quality: "Dobra+",
  },
  {
    id: "iterative_multihop",
    label: "MultiHop",
    tag: "WIELOETAPOWY",
    Icon: GitMerge,
    desc: "Rozkłada pytanie na pod-pytania i odpowiada na każde osobno. Idealny do pytań złożonych.",
    avgTime: "~9s",
    quality: "Wysoka",
  },
  {
    id: "madam_rag",
    label: "MADAM",
    tag: "SPRZECZNOŚCI",
    Icon: AlertTriangle,
    desc: "Wykrywa konflikty między dokumentami i sygnalizuje niejednoznaczności. Kluczowy przy sprzecznych źródłach.",
    avgTime: "~8s",
    quality: "Wysoka",
  },
  {
    id: "rare_rag",
    label: "RARE",
    tag: "AUTO-ROUTING",
    Icon: Shuffle,
    desc: "Analizuje pytanie i automatycznie wybiera najlepszy tryb RAG. Najinteligentniejszy, ale najwolniejszy.",
    avgTime: "~12s",
    quality: "Najwyższa",
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

"use client";
import { useState } from "react";
import { ChevronDown, Quote, FileText, Copy, Info } from "lucide-react";
import { useTranslations } from "next-intl";
import { Citation } from "@/lib/api";

interface CitationCardProps {
  citation: Citation;
  n: number;
  focused: boolean;
  onFocus: () => void;
  compact?: boolean;
}

const RelevanceBar = ({ relevance }: { relevance?: number | null }) => {
  if (relevance == null) return null;
  const pct = Math.round(relevance * 100);
  return (
    <div className="cite-rel">
      <div className="cite-rel-track">
        <div className="cite-rel-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="cite-rel-num">{pct}%</span>
    </div>
  );
};

export function CitationCard({ citation, n, focused, onFocus, compact }: CitationCardProps) {
  const t = useTranslations("chat");
  return (
    <button
      className={`cite-card${focused ? " cite-card-focus" : ""}${compact ? " cite-card-compact" : ""}`}
      onClick={onFocus}
    >
      <div className="cite-card-top">
        <span className="cite-num">{n}</span>
        <div className="cite-card-meta">
          <div className="cite-card-doc">{citation.filename ?? t("fragmentFallback", { n })}</div>
          <div className="cite-card-sub">
            <span className="cite-card-file">{citation.filename ?? citation.chunk_id.slice(0, 20)}</span>
            {citation.page != null && (
              <>
                <span className="cite-dot" />
                <span>{t("pageNum", { n: citation.page })}</span>
              </>
            )}
          </div>
        </div>
      </div>
      <div className="cite-card-snippet">"{citation.snippet}"</div>
      <div className="cite-card-foot">
        <RelevanceBar relevance={citation.relevance} />
      </div>
    </button>
  );
}

interface CardsProps {
  citations: Citation[];
  revealed: number;
  focused: string | null;
  onFocus: (id: string) => void;
}

export function CitationsCards({ citations, revealed, focused, onFocus }: CardsProps) {
  const t = useTranslations("chat");
  const [expanded, setExpanded] = useState(false);
  if (!citations.length) return null;

  return (
    <div className={`cite-cards-wrap${expanded ? " cite-cards-open" : " cite-cards-collapsed"}`}>
      <button type="button" className="cite-cards-head cite-cards-head-btn" onClick={() => setExpanded(!expanded)}>
        <div className="cite-cards-t">
          <Quote size={15} />
          <span>{t("citedSources", { n: Math.min(revealed, citations.length) })}</span>
        </div>
        <span className="cite-cards-btn cite-cards-toggle">
          <span>{expanded ? t("hide") : t("show")}</span>
          <ChevronDown size={13} className="cite-cards-chev" />
        </span>
      </button>
      {expanded && (
        <div className="cite-cards-grid stagger">
          {citations.slice(0, revealed).map((c, i) => (
            <CitationCard
              key={c.chunk_id}
              citation={c}
              n={c.n ?? i + 1}
              focused={focused === c.chunk_id}
              onFocus={() => onFocus(c.chunk_id)}
              compact
            />
          ))}
          {Array.from({ length: Math.max(0, citations.length - revealed) }).map((_, i) => (
            <div key={`skel-${i}`} className="cite-skel cite-skel-pending">
              <span /><span /><span />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface SidebarProps {
  citations: Citation[];
  revealed: number;
  focused: string | null;
  onFocus: (id: string) => void;
  isLoading?: boolean;
}

export function CitationsSidebar({ citations, revealed, focused, onFocus, isLoading }: SidebarProps) {
  const t = useTranslations("chat");
  const [expanded, setExpanded] = useState(true);

  return (
    <div className={`cite-sidebar${expanded ? " cite-sidebar-open" : " cite-sidebar-collapsed"}`}>
      <button type="button" className="cite-side-head cite-side-head-btn" onClick={() => setExpanded(!expanded)}>
        <div>
          <div className="cite-side-t">{t("sidebarSources")}</div>
          <div className="cite-side-s">
            {isLoading
              ? t("waitingForFragments")
              : t("revealedStatus", { revealed: Math.min(revealed, citations.length), total: citations.length })}
          </div>
        </div>
        <ChevronDown size={16} className="cite-side-chev" />
      </button>
      {expanded && (
        <>
          <div className="cite-side-list">
            {isLoading && (
              <>
                {[0, 1, 2].map((i) => (
                  <div key={i} className="cite-skel"><span /><span /><span /></div>
                ))}
              </>
            )}
            {!isLoading && citations.slice(0, revealed).map((c, i) => (
              <CitationCard
                key={c.chunk_id}
                citation={c}
                n={c.n ?? i + 1}
                focused={focused === c.chunk_id}
                onFocus={() => onFocus(c.chunk_id)}
              />
            ))}
            {!isLoading && Array.from({ length: Math.max(0, citations.length - revealed) }).map((_, i) => (
              <div key={`skel-${i}`} className="cite-skel cite-skel-pending"><span /><span /><span /></div>
            ))}
          </div>
          <div className="cite-side-hint">
            <Info size={13} />
            <span>{t.rich("sidebarHint", { strong: (chunks) => <strong>{chunks}</strong> })}</span>
          </div>
        </>
      )}
    </div>
  );
}

interface InlineProps {
  citations: Citation[];
  revealed: number;
  focused: string | null;
  onFocus: (id: string) => void;
}

export function CitationsInline({ citations, revealed, focused, onFocus }: InlineProps) {
  const t = useTranslations("chat");
  const [expanded, setExpanded] = useState(true);
  const [openOne, setOpenOne] = useState<string | null>(null);
  if (!citations.length) return null;

  return (
    <div className={`cite-inline${expanded ? " cite-inline-wrap-open" : " cite-inline-wrap-collapsed"}`} style={{ marginTop: 18 }}>
      <button type="button" className="cite-inline-head cite-inline-head-btn" onClick={() => setExpanded(!expanded)}>
        <Quote size={14} />
        <span>{t("footnotesTitle", { n: Math.min(revealed, citations.length) })}</span>
        <ChevronDown size={14} className="cite-inline-head-chev" />
      </button>
      {expanded && citations.slice(0, revealed).map((c, i) => {
        const open = openOne === c.chunk_id;
        return (
          <div key={c.chunk_id} className={`cite-inline-row${open ? " cite-inline-open" : ""}`}>
            <button className="cite-inline-summary" onClick={() => setOpenOne(open ? null : c.chunk_id)}>
              <span className="cite-num cite-num-sm">{c.n ?? i + 1}</span>
              <div className="cite-inline-meta">
                <div className="cite-inline-doc">{c.filename ?? t("fragmentFallback", { n: i + 1 })}</div>
                <div className="cite-inline-sub">
                  {c.filename ?? c.chunk_id.slice(0, 20)}{c.page != null ? ` · ${t("pageNum", { n: c.page })}` : ""}
                </div>
              </div>
              <RelevanceBar relevance={c.relevance} />
              <ChevronDown size={14} className="cite-inline-chevron" />
            </button>
            {open && (
              <div className="cite-inline-body fade-up">
                <p>"{c.snippet}"</p>
                <div className="cite-inline-actions">
                  <button className="btn-ghost cite-inline-act"><FileText size={12} /> {t("openDocument")}</button>
                  <button className="btn-ghost cite-inline-act"><Copy size={12} /> {t("copySnippet")}</button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

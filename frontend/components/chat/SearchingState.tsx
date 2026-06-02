"use client";
import { useState, useEffect } from "react";
import { FileText, CheckCircle2, ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { ScannedDoc } from "@/lib/api";

interface Props {
  docs?: ScannedDoc[];
  progress?: number;   // 0..1
  done?: boolean;
}

export default function SearchingState({ docs = [], progress = 0, done = false }: Props) {
  const t = useTranslations("chat");
  const [expanded, setExpanded] = useState(true);
  const doneCount = done ? docs.length : docs.filter((d) => d.done).length;

  useEffect(() => {
    if (done) setExpanded(false);
  }, [done]);

  return (
    <div className="search-state fade-up">
      <button
        type="button"
        className="search-state-h search-state-h-btn"
        onClick={() => done && setExpanded(!expanded)}
        style={{ cursor: done ? "pointer" : "default" }}
      >
        {done
          ? <CheckCircle2 size={16} style={{ color: "var(--c-accent-mint)", flexShrink: 0 }} />
          : <div className="search-spinner" />}
        <div style={{ flex: 1 }}>
          <div className="search-state-t">
            {done ? t("searchedTitle") : t("searchingTitle")}
          </div>
          <div className="search-state-s">
            {t("searchingSubtitle", { n: docs.length || "…" })}
          </div>
        </div>
        {docs.length > 0 && (
          <div className="search-state-cnt">
            {doneCount} / {docs.length}
          </div>
        )}
        {done && (
          <ChevronDown
            size={14}
            style={{
              color: "var(--text-muted)",
              flexShrink: 0,
              transform: expanded ? "rotate(180deg)" : "",
              transition: "transform var(--t-fast) var(--ease)",
            }}
          />
        )}
      </button>

      {(!done || expanded) && docs.length > 0 && (
        <div className="search-docs">
          {docs.map((doc, i) => {
            const isDone = done || doc.done;
            const isActive = !isDone && !done && (i / docs.length) <= progress;
            return (
              <div
                key={i}
                className={`search-doc${isDone ? " search-doc-done" : ""}${isActive ? " search-doc-active" : ""}`}
              >
                <FileText size={14} className="search-doc-ic" />
                <span className="search-doc-name">{doc.name}</span>
                <span className="search-doc-bar">
                  <span className="search-doc-bar-fill" />
                </span>
                <span className="search-doc-hits">
                  {isDone
                    ? doc.hits > 0
                      ? <><strong>{doc.hits}</strong> {t("chunksUsed", { n: "" }).split(" ")[0]}</>
                      : <CheckCircle2 size={12} style={{ color: "var(--c-accent-mint)" }} />
                    : isActive
                    ? <span className="search-doc-loading">{t("searchScan")}</span>
                    : <span className="search-doc-pending">—</span>}
                </span>
                {isDone && <CheckCircle2 size={13} className="search-doc-check" />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

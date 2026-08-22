"use client";
import React from "react";
import { normalizeCitationMarkers } from "@/lib/citations";

interface Cite { chunk_id: string; n?: number }

interface Props {
  text: string;
  citations: Cite[];
  focusedId: string | null;
  onCiteClick: (id: string) => void;
  streaming?: boolean;
}

/**
 * Resolve a [n] marker to a citation. Only *cited* sources are returned by the
 * backend, so the marker number is not the array position: an answer citing
 * SOURCE_1/2/3/5 yields four citations, and [5] must map to the fourth, not to
 * citations[4]. Match on the `n` field, falling back to position for older
 * conversations stored before `n` existed.
 */
function resolveCite(citations: Cite[], n: number): Cite | undefined {
  if (citations.some((c) => c.n != null)) return citations.find((c) => c.n === n);
  return citations[n - 1];
}

interface InlineCtx {
  citations: Cite[];
  onCiteClick: (id: string) => void;
  focusedId: string | null;
}

/** Bold, italic, inline code and citation chips, in one pass. */
function inline(s: string, ctx: InlineCtx, keyPrefix: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*)|(__[^_]+__)|(\*[^*\n]+\*)|(`[^`\n]+`)|(\[\d+\](?:\s*\[\d+\])*)/g;
  let last = 0;
  let key = 0;
  let m: RegExpExecArray | null;

  const citeChip = (n: number): React.ReactNode | null => {
    const cit = resolveCite(ctx.citations, n);
    if (!cit) return null; // orphaned marker — the model numbered from a larger pool
    return (
      <button
        key={`${keyPrefix}r${key++}`}
        className={`cite-ref${ctx.focusedId === cit.chunk_id ? " cite-ref-focus" : ""}`}
        onClick={() => ctx.onCiteClick(cit.chunk_id)}
        aria-label={`Source ${n}`}
      >
        {n}
      </button>
    );
  };

  while ((m = regex.exec(s)) !== null) {
    if (m.index > last) parts.push(s.slice(last, m.index));
    if (m[1] || m[2]) {
      const inner = (m[1] ?? m[2]).slice(2, -2);
      parts.push(<strong key={`${keyPrefix}b${key++}`}>{inline(inner, ctx, `${keyPrefix}b${key}`)}</strong>);
    } else if (m[3]) {
      parts.push(<em key={`${keyPrefix}i${key++}`}>{m[3].slice(1, -1)}</em>);
    } else if (m[4]) {
      parts.push(<code key={`${keyPrefix}c${key++}`} className="ans-code">{m[4].slice(1, -1)}</code>);
    } else if (m[5]) {
      for (const ref of m[5].match(/\[\d+\]/g) ?? []) {
        const chip = citeChip(parseInt(ref.slice(1, -1), 10));
        if (chip) parts.push(chip);
      }
    }
    last = m.index + m[0].length;
  }
  if (last < s.length) parts.push(s.slice(last));
  return parts;
}

const isTableRow = (l: string) => l.trim().startsWith("|") && l.trim().endsWith("|");
const isTableDivider = (l: string) => /^\s*\|[\s:|-]+\|\s*$/.test(l);
const splitRow = (l: string) =>
  l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

function renderAnswer(text: string, ctx: InlineCtx): React.ReactNode[] {
  const lines = normalizeCitationMarkers(text).split("\n");
  const out: React.ReactNode[] = [];
  let key = 0;
  let buf: string[] = [];

  const flushPara = () => {
    if (buf.length) {
      out.push(<p key={`p${key++}`}>{inline(buf.join(" "), ctx, `p${key}`)}</p>);
      buf = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed === "") { flushPara(); continue; }

    // Table: header row, divider, then body rows.
    if (isTableRow(line) && i + 1 < lines.length && isTableDivider(lines[i + 1])) {
      flushPara();
      const header = splitRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && isTableRow(lines[i])) { rows.push(splitRow(lines[i])); i++; }
      i--;
      out.push(
        <div key={`tw${key++}`} className="ans-table-wrap">
          <table className="ans-table">
            <thead>
              <tr>{header.map((h, hi) => <th key={hi}>{inline(h, ctx, `th${key}${hi}`)}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri}>{r.map((c, ci) => <td key={ci}>{inline(c, ctx, `td${key}${ri}${ci}`)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    const heading = /^(#{1,4})\s+(.*)$/.exec(trimmed);
    if (heading) {
      flushPara();
      const level = Math.min(6, heading[1].length + 2);
      const Tag = `h${level}` as "h3" | "h4" | "h5" | "h6";
      out.push(<Tag key={`h${key++}`} className="ans-heading">{inline(heading[2], ctx, `h${key}`)}</Tag>);
      continue;
    }

    if (/^([-*•])\s+/.test(trimmed)) {
      flushPara();
      const items: string[] = [];
      while (i < lines.length && /^([-*•])\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^([-*•])\s+/, ""));
        i++;
      }
      i--;
      out.push(
        <ul key={`u${key++}`} className="ans-list">
          {items.map((it, idx) => <li key={idx}>{inline(it, ctx, `u${key}${idx}`)}</li>)}
        </ul>
      );
      continue;
    }

    if (/^\d+[.)]\s+/.test(trimmed)) {
      flushPara();
      const items: string[] = [];
      while (i < lines.length && /^\d+[.)]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+[.)]\s+/, ""));
        i++;
      }
      i--;
      out.push(
        <ol key={`o${key++}`} className="ans-list ans-list-ordered">
          {items.map((it, idx) => <li key={idx}>{inline(it, ctx, `o${key}${idx}`)}</li>)}
        </ol>
      );
      continue;
    }

    if (trimmed.startsWith("> ")) {
      flushPara();
      out.push(
        <blockquote key={`q${key++}`} className="ans-quote">
          {inline(trimmed.slice(2), ctx, `q${key}`)}
        </blockquote>
      );
      continue;
    }

    buf.push(line);
  }
  flushPara();
  return out;
}

export default function MessageAnswer({ text, citations, focusedId, onCiteClick, streaming }: Props) {
  return (
    <div className="msg-answer">
      {renderAnswer(text, { citations, onCiteClick, focusedId })}
      {streaming && <span className="stream-cursor" aria-hidden="true" />}
    </div>
  );
}

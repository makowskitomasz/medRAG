"use client";
import React from "react";

interface Props {
  text: string;
  citations: Array<{ chunk_id: string }>;
  focusedId: string | null;
  onCiteClick: (id: string) => void;
  streaming?: boolean;
}

function normalizeText(text: string): string {
  // 【SOURCE_n†...】 format (stored in DB from older runs)
  let out = text.replace(/【SOURCE_(\d+)[^】]*】/g, "[$1]");
  // [SOURCE_n] format (current LLM output)
  out = out.replace(/\[SOURCE_(\d+)\]/g, "[$1]");
  return out;
}

function renderAnswer(
  text: string,
  citations: Array<{ chunk_id: string }>,
  onCiteClick: (id: string) => void,
  focusedId: string | null
): React.ReactNode[] {
  const lines = normalizeText(text).split("\n");
  const out: React.ReactNode[] = [];
  let key = 0;

  const inline = (s: string): React.ReactNode[] => {
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*[^*]+\*\*)|(\[\d+\](?:\[\d+\])*)/g;
    let last = 0;
    let m: RegExpExecArray | null;
    while ((m = regex.exec(s)) !== null) {
      if (m.index > last) parts.push(s.slice(last, m.index));
      if (m[1]) {
        const boldText = m[1].slice(2, -2);
        const boldParts: React.ReactNode[] = [];
        const citeRx = /\[(\d+)\]/g;
        let bLast = 0; let bm: RegExpExecArray | null;
        while ((bm = citeRx.exec(boldText)) !== null) {
          if (bm.index > bLast) boldParts.push(boldText.slice(bLast, bm.index));
          const bn = parseInt(bm[1], 10);
          const bcit = citations[bn - 1];
          if (bcit) {
            const bcid = bcit.chunk_id;
            boldParts.push(
              <button key={"r" + key++} className={`cite-ref${focusedId === bcid ? " cite-ref-focus" : ""}`} onClick={() => onCiteClick(bcid)}>{bn}</button>
            );
          }
          bLast = bm.index + bm[0].length;
        }
        if (bLast < boldText.length) boldParts.push(boldText.slice(bLast));
        parts.push(<strong key={"b" + key++}>{boldParts}</strong>);
      } else if (m[2]) {
        const refs = m[2].match(/\[\d+\]/g) ?? [];
        refs.forEach((r) => {
          const n = parseInt(r.slice(1, -1), 10);
          const cit = citations[n - 1];
          if (!cit) return; // orphaned citation — LLM numbered from larger pool
          const cid = cit.chunk_id;
          parts.push(
            <button
              key={"r" + key++}
              className={`cite-ref${focusedId === cid ? " cite-ref-focus" : ""}`}
              onClick={() => onCiteClick(cid)}
            >
              {n}
            </button>
          );
        });
      }
      last = m.index + m[0].length;
    }
    if (last < s.length) parts.push(s.slice(last));
    return parts;
  };

  let buf: string[] = [];
  const flushPara = () => {
    if (buf.length) {
      out.push(<p key={"p" + key++}>{inline(buf.join(" "))}</p>);
      buf = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === "") { flushPara(); continue; }
    if (line.startsWith("• ") || line.startsWith("- ")) {
      flushPara();
      const items: string[] = [];
      while (i < lines.length && (lines[i].startsWith("• ") || lines[i].startsWith("- "))) {
        items.push(lines[i].slice(2));
        i++;
      }
      i--;
      out.push(
        <ul key={"u" + key++} className="ans-list">
          {items.map((it, idx) => <li key={idx}>{inline(it)}</li>)}
        </ul>
      );
    } else if (line.startsWith("> ")) {
      flushPara();
      out.push(<blockquote key={"q" + key++} className="ans-quote">{inline(line.slice(2))}</blockquote>);
    } else {
      buf.push(line);
    }
  }
  flushPara();
  return out;
}

export default function MessageAnswer({ text, citations, focusedId, onCiteClick, streaming }: Props) {
  return (
    <div className="msg-answer">
      {renderAnswer(text, citations, onCiteClick, focusedId)}
      {streaming && <span className="stream-cursor" />}
    </div>
  );
}

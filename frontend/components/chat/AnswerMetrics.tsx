"use client";
import { Clock, Coins } from "lucide-react";
import { useTranslations } from "next-intl";

interface Props {
  /** Wall time measured by the client, from send to the last streamed token. */
  elapsedMs?: number;
  inputTokens?: number;
  outputTokens?: number;
}

function formatTokens(n: number): string {
  return n >= 10_000 ? `${(n / 1000).toFixed(1)}k` : n.toLocaleString();
}

/**
 * Cost and speed of the answer. Both values are known the moment the stream ends
 * — the client times the request itself and generation reports usage on its final
 * event — so nothing here waits on the asynchronous evaluation pipeline.
 *
 * Quality scores (faithfulness, relevance, citation precision) are deliberately
 * absent: they belong in the benchmark results, not beside a single answer.
 */
export default function AnswerMetrics({ elapsedMs, inputTokens, outputTokens }: Props) {
  const t = useTranslations("chat");

  const total = (inputTokens ?? 0) + (outputTokens ?? 0);
  if (elapsedMs == null && !total) return null;

  return (
    <div className="ans-metrics">
      {elapsedMs != null && (
        <span className="ans-metric" title={t("elapsedLabel")}>
          <Clock size={11} aria-hidden="true" />
          <span className="ans-metric-v">{(elapsedMs / 1000).toFixed(1)}s</span>
        </span>
      )}
      {total > 0 && (
        <span
          className="ans-metric"
          title={t("tokensBreakdown", { in: inputTokens ?? 0, out: outputTokens ?? 0 })}
        >
          <Coins size={11} aria-hidden="true" />
          <span className="ans-metric-v">{formatTokens(total)}</span>
          <span className="ans-metric-k">{t("metric_tokens")}</span>
        </span>
      )}
    </div>
  );
}

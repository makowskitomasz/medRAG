"use client";
import { Clock, Coins } from "lucide-react";
import { useTranslations } from "next-intl";
import { AnswerMetrics as Metrics } from "@/lib/api";

interface Props {
  metrics?: Metrics | null;
}

function formatTokens(n: number): string {
  return n >= 10_000 ? `${(n / 1000).toFixed(1)}k` : n.toLocaleString();
}

/**
 * Cost and speed of the answer, from the `eval` service. Quality scores
 * (faithfulness, relevance, citation precision) are deliberately not shown here —
 * they belong in the benchmark results, not next to a single answer.
 */
export default function AnswerMetrics({ metrics }: Props) {
  const t = useTranslations("chat");
  if (!metrics) return null;

  const latency = typeof metrics.latency_ms === "number" ? metrics.latency_ms : null;
  const inTok = typeof metrics.input_tokens === "number" ? metrics.input_tokens : null;
  const outTok = typeof metrics.output_tokens === "number" ? metrics.output_tokens : null;
  const total = typeof metrics.token_count === "number"
    ? metrics.token_count
    : (inTok ?? 0) + (outTok ?? 0);

  if (latency == null && !total) return null;

  return (
    <div className="ans-metrics">
      {latency != null && (
        <span className="ans-metric" title={t("metric_latency_ms")}>
          <Clock size={11} aria-hidden="true" />
          <span className="ans-metric-v">{(latency / 1000).toFixed(1)}s</span>
        </span>
      )}
      {total > 0 && (
        <span
          className="ans-metric"
          title={
            inTok != null && outTok != null
              ? t("tokensBreakdown", { in: inTok, out: outTok })
              : t("metric_tokens")
          }
        >
          <Coins size={11} aria-hidden="true" />
          <span className="ans-metric-v">{formatTokens(total)}</span>
          <span className="ans-metric-k">{t("metric_tokens")}</span>
        </span>
      )}
    </div>
  );
}

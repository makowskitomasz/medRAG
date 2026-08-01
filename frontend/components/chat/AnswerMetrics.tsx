"use client";
import { BarChart3 } from "lucide-react";
import { useTranslations } from "next-intl";
import { AnswerMetrics as Metrics } from "@/lib/api";

interface Props {
  metrics?: Metrics | null;
}

/** Metrics shown as 0–1 scores; latency is rendered separately as a duration. */
const SCORE_KEYS = [
  "faithfulness",
  "answer_relevance",
  "citation_precision",
  "token_f1",
] as const;

function tone(v: number): string {
  if (v >= 0.8) return "metric-good";
  if (v >= 0.5) return "metric-mid";
  return "metric-low";
}

/**
 * Per-answer evaluation from the `eval` service. Streamed queries never published
 * `query.completed`, so no answer produced in the UI used to have metrics at all.
 */
export default function AnswerMetrics({ metrics }: Props) {
  const t = useTranslations("chat");
  if (!metrics) return null;

  const scores = SCORE_KEYS.filter((k) => typeof metrics[k] === "number").map((k) => ({
    key: k,
    value: metrics[k] as number,
  }));
  const latency = typeof metrics.latency_ms === "number" ? metrics.latency_ms : null;
  if (!scores.length && latency == null) return null;

  return (
    <div className="ans-metrics">
      <span className="ans-metrics-h">
        <BarChart3 size={12} aria-hidden="true" />
        {t("metricsTitle")}
      </span>
      {scores.map(({ key, value }) => (
        <span key={key} className={`ans-metric ${tone(value)}`} title={t(`metric_${key}`)}>
          <span className="ans-metric-k">{t(`metric_${key}`)}</span>
          <span className="ans-metric-v">{value.toFixed(2)}</span>
        </span>
      ))}
      {latency != null && (
        <span className="ans-metric" title={t("metric_latency_ms")}>
          <span className="ans-metric-k">{t("metric_latency_ms")}</span>
          <span className="ans-metric-v">{(latency / 1000).toFixed(1)}s</span>
        </span>
      )}
    </div>
  );
}

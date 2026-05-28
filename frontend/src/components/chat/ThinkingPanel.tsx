"use client"

import { Brain, Search, Users } from "lucide-react"
import { cn } from "@/lib/utils"
import type { SearchEvent, ThinkEvent, ChatPhase } from "@/hooks/useChatStream"

interface Props {
  phase: ChatPhase
  searchEvents: SearchEvent[]
  thinkEvents: ThinkEvent[]
  ragMode: string
}

export function ThinkingPanel({ phase, searchEvents, thinkEvents, ragMode }: Props) {
  if (phase === "idle" || phase === "done") return null

  const isMultiAgent = ragMode === "multi_agent"
  const isSelfReflection = ragMode === "self_reflection"

  return (
    <div className="mb-3 rounded-lg border border-[hsl(var(--thinking-border))] bg-[hsl(var(--thinking-bg))] overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[hsl(var(--thinking-border))]">
        {isMultiAgent ? (
          <Users className="h-3.5 w-3.5 text-[hsl(var(--thinking-text))]" />
        ) : (
          <Brain className="h-3.5 w-3.5 text-[hsl(var(--thinking-text))]" />
        )}
        <span className="text-xs font-medium text-[hsl(var(--thinking-text))]">
          {phase === "searching" ? "Wyszukiwanie…" : phase === "thinking" ? "Analiza…" : "Generowanie…"}
        </span>
        {(phase === "searching" || phase === "thinking" || phase === "streaming") && (
          <div className="ml-auto flex gap-1">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-1 h-1 rounded-full bg-[hsl(var(--thinking-text))] opacity-60"
                style={{
                  animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                }}
              />
            ))}
          </div>
        )}
      </div>

      <div className="px-4 py-3 space-y-1.5">
        {/* Search progress */}
        {searchEvents.map((ev, i) => (
          <SearchStep key={i} event={ev} />
        ))}

        {/* Think steps */}
        {thinkEvents.map((ev, i) => (
          <ThinkStep key={i} event={ev} />
        ))}
      </div>
    </div>
  )
}

function SearchStep({ event }: { event: SearchEvent }) {
  return (
    <div className="flex items-start gap-2 text-xs text-[hsl(var(--thinking-text))]">
      <Search className="h-3 w-3 mt-0.5 shrink-0 opacity-60" />
      <span>
        {event.status === "searching" && `Wyszukiwanie: "${event.query ?? ""}"`}
        {event.status === "reranking" && `Rerankowanie ${event.found ?? 0} fragmentów…`}
        {event.status === "done" && `Wybrano ${event.kept ?? 0} fragmentów`}
      </span>
    </div>
  )
}

function ThinkStep({ event }: { event: ThinkEvent }) {
  return (
    <div className="flex items-start gap-2 text-xs text-[hsl(var(--thinking-text))]">
      <Brain className="h-3 w-3 mt-0.5 shrink-0 opacity-60" />
      <span>
        <span className="font-medium">{event.step}</span>
        {event.note && <span className="opacity-70"> — {event.note}</span>}
      </span>
    </div>
  )
}

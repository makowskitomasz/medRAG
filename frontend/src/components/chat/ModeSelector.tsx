"use client"

import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

const MODES = [
  {
    value: "vanilla",
    label: "Vanilla",
    description: "Klasyczne wyszukiwanie hybrydowe BM25 + wektor",
  },
  {
    value: "hyde",
    label: "HyDE",
    description: "Generuje hipotetyczny dokument do rozszerzenia zapytania",
  },
  {
    value: "query_rewriting",
    label: "Rewrite",
    description: "Przepisuje zapytanie z uwzględnieniem kontekstu rozmowy",
  },
  {
    value: "self_reflection",
    label: "Reflect",
    description: "Iteracyjna samoocena — powtarza wyszukiwanie gdy odpowiedź niewystarczająca",
  },
  {
    value: "multi_agent",
    label: "Multi-Agent",
    description: "Równolegle wyszukuje z 3 perspektyw: mechanizm, ryzyko, dawkowanie",
  },
] as const

export type RagMode = (typeof MODES)[number]["value"]

interface Props {
  value: RagMode
  onChange: (v: RagMode) => void
  disabled?: boolean
}

export function ModeSelector({ value, onChange, disabled }: Props) {
  return (
    <div
      className="flex items-center gap-1 p-1 rounded-lg bg-muted/60 border border-border"
      role="radiogroup"
      aria-label="Tryb RAG"
    >
      {MODES.map((m) => (
        <Tooltip key={m.value}>
          <TooltipTrigger>
            <button
              type="button"
              role="radio"
              aria-checked={value === m.value}
              disabled={disabled}
              onClick={() => onChange(m.value)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-colors select-none",
                value === m.value
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-background/50",
                disabled && "opacity-50 cursor-not-allowed"
              )}
            >
              {m.label}
            </button>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-[200px] text-center text-xs">
            {m.description}
          </TooltipContent>
        </Tooltip>
      ))}
    </div>
  )
}

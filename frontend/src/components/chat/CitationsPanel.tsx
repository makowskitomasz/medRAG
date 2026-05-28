"use client"

import { ExternalLink, FileText } from "lucide-react"
import { cn } from "@/lib/utils"
import type { Citation } from "@/lib/api"
import type { CitationLayout } from "@/store/tweaks"
import { Badge } from "@/components/ui/badge"

interface Props {
  citations: Citation[]
  layout: CitationLayout
}

export function CitationsPanel({ citations, layout }: Props) {
  if (!citations || citations.length === 0) return null

  if (layout === "sidebar") return <CitationsSidebar citations={citations} />
  if (layout === "cards") return <CitationsCards citations={citations} />
  return <CitationsInline citations={citations} />
}

function CitationsSidebar({ citations }: { citations: Citation[] }) {
  return (
    <aside className="w-72 shrink-0 border-l border-border bg-muted/30 overflow-y-auto">
      <div className="p-3 border-b border-border">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Źródła ({citations.length})
        </h3>
      </div>
      <div className="divide-y divide-border">
        {citations.map((c) => (
          <CitationCard key={c.n} citation={c} variant="sidebar" />
        ))}
      </div>
    </aside>
  )
}

function CitationsCards({ citations }: { citations: Citation[] }) {
  return (
    <div className="mt-4 border-t border-border pt-4">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
        Źródła ({citations.length})
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {citations.map((c) => (
          <CitationCard key={c.n} citation={c} variant="card" />
        ))}
      </div>
    </div>
  )
}

function CitationsInline({ citations }: { citations: Citation[] }) {
  return (
    <div className="mt-3 space-y-1.5">
      {citations.map((c) => (
        <div key={c.n} className="flex items-start gap-2 text-xs text-muted-foreground">
          <span className="citation-marker shrink-0">{c.n}</span>
          <span className="line-clamp-2">{c.snippet}</span>
        </div>
      ))}
    </div>
  )
}

function CitationCard({
  citation: c,
  variant,
}: {
  citation: Citation
  variant: "sidebar" | "card"
}) {
  return (
    <div
      className={cn(
        "group",
        variant === "sidebar" && "p-3",
        variant === "card" && "p-3 rounded-lg border border-border bg-background hover:border-[hsl(var(--accent-300))] transition-colors"
      )}
    >
      <div className="flex items-start gap-2">
        <span className="citation-marker shrink-0">{c.n}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <FileText className="h-3 w-3 text-muted-foreground shrink-0" />
            <span className="text-xs font-medium truncate">{c.filename ?? c.documentId}</span>
            {c.page && (
              <Badge variant="secondary" className="text-xs px-1 py-0 h-4 shrink-0">
                s. {c.page}
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">{c.snippet}</p>
        </div>
      </div>
    </div>
  )
}

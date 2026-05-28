"use client"

import { useQuery } from "@tanstack/react-query"
import { projectsApi } from "@/lib/api"
import { Topbar } from "@/components/layout/Topbar"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Settings, Database, Layers } from "lucide-react"

export default function AdminPage() {
  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list(),
  })

  return (
    <div className="flex flex-col h-full">
      <Topbar title="Administracja" />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-8">
          {/* Projects */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Database className="h-5 w-5 text-muted-foreground" />
              <h2 className="text-base font-semibold">Projekty</h2>
            </div>

            {isLoading && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {[1, 2].map((i) => <Skeleton key={i} className="h-32" />)}
              </div>
            )}

            {projects && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {projects.map((p) => (
                  <div key={p.project_id} className="p-4 rounded-xl border border-border bg-background">
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <h3 className="font-medium text-sm">{p.name}</h3>
                      <Badge variant="outline" className="text-xs shrink-0">{p.settings.rag_mode}</Badge>
                    </div>

                    {p.description && (
                      <p className="text-xs text-muted-foreground mb-3">{p.description}</p>
                    )}

                    <div className="grid grid-cols-2 gap-y-1.5 text-xs">
                      <Setting label="Chunking" value={p.settings.chunking_strategy} />
                      <Setting label="Top-k" value={String(p.settings.top_k)} />
                      <Setting label="Alpha" value={String(p.settings.hybrid_alpha)} />
                      <Setting label="Rerank top-n" value={String(p.settings.rerank_top_n)} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

function Setting({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-muted-foreground">{label}: </span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

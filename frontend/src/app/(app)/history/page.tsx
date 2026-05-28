"use client"

import Link from "next/link"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { conversationsApi } from "@/lib/api"
import { useAppStore } from "@/store/app"
import { Topbar } from "@/components/layout/Topbar"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Trash2, MessageSquare } from "lucide-react"
import { toast } from "sonner"
import { formatDistanceToNow } from "@/lib/date"

export default function HistoryPage() {
  const { activeProjectId } = useAppStore()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["conversations", activeProjectId],
    queryFn: () => conversationsApi.list(activeProjectId ?? undefined),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conversations"] })
      toast.success("Rozmowa usunięta")
    },
  })

  return (
    <div className="flex flex-col h-full">
      <Topbar title="Historia rozmów" />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto">
          {isLoading && (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
            </div>
          )}

          {!isLoading && (!data || data.length === 0) && (
            <div className="text-center py-20">
              <MessageSquare className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
              <p className="text-muted-foreground text-sm">Brak rozmów</p>
              <Link href="/chat">
                <Button variant="outline" className="mt-4" size="sm">Nowa rozmowa</Button>
              </Link>
            </div>
          )}

          {data && data.length > 0 && (
            <div className="space-y-2">
              {data.map((conv) => (
                <div key={conv.id} className="group flex items-center gap-3 p-4 rounded-xl border border-border hover:border-[hsl(var(--accent-300))] bg-background hover:bg-muted/30 transition-colors">
                  <Link href={`/chat/${conv.id}`} className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-medium truncate">{conv.title ?? "Nowa rozmowa"}</p>
                      <Badge variant="secondary" className="text-xs shrink-0">{conv.rag_mode}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {conv.message_count} wiadomości · {formatDistanceToNow(conv.updated_at)}
                    </p>
                  </Link>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                    onClick={() => deleteMutation.mutate(conv.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

"use client"

import { useEffect, useRef } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useChatStream } from "@/hooks/useChatStream"
import { useAppStore } from "@/store/app"
import { useTweaks } from "@/store/tweaks"
import { MessageBubble } from "@/components/chat/MessageBubble"
import { CitationsPanel } from "@/components/chat/CitationsPanel"
import { ChatInput } from "@/components/chat/ChatInput"
import { ModeSelector, type RagMode } from "@/components/chat/ModeSelector"
import { Topbar } from "@/components/layout/Topbar"
import { useState } from "react"
import { Skeleton } from "@/components/ui/skeleton"

export default function ChatPage() {
  const { activeProjectId } = useAppStore()
  const { citationLayout } = useTweaks()
  const [ragMode, setRagMode] = useState<RagMode>("vanilla")

  const { messages, phase, error, send, cancel } = useChatStream(activeProjectId)

  const scrollRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages])

  const lastMessage = messages[messages.length - 1]
  const lastCitations =
    lastMessage?.role === "assistant" ? (lastMessage.citations ?? []) : []

  const showSidebar = citationLayout === "sidebar" && lastCitations.length > 0

  return (
    <div className="flex flex-col h-full">
      <Topbar title="Nowa rozmowa" />

      <div className="flex flex-1 min-h-0">
        {/* Chat area */}
        <div className="flex flex-col flex-1 min-w-0">
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.length === 0 && (
                <EmptyState />
              )}

              {messages.map((msg, i) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  isLast={i === messages.length - 1}
                  phase={phase}
                  citationLayout={citationLayout}
                  ragMode={ragMode}
                />
              ))}

              {/* Inline/cards citations for last message */}
              {citationLayout !== "sidebar" && lastCitations.length > 0 && (
                <CitationsPanel citations={lastCitations} layout={citationLayout} />
              )}

              {error && (
                <div className="text-sm text-destructive bg-destructive/10 px-4 py-3 rounded-lg">
                  Błąd: {error}
                </div>
              )}
            </div>
          </div>

          {/* Mode selector + input */}
          <div>
            <div className="px-4 pb-2">
              <div className="max-w-3xl mx-auto">
                <ModeSelector
                  value={ragMode}
                  onChange={setRagMode}
                  disabled={phase !== "idle" && phase !== "done" && phase !== "error"}
                />
              </div>
            </div>
            <ChatInput
              onSend={send}
              onCancel={cancel}
              phase={phase}
              disabled={!activeProjectId}
            />
            {!activeProjectId && (
              <p className="text-xs text-center text-muted-foreground pb-2">
                Wybierz projekt w górnym pasku, aby rozpocząć rozmowę
              </p>
            )}
          </div>
        </div>

        {/* Citations sidebar */}
        {showSidebar && (
          <CitationsPanel citations={lastCitations} layout="sidebar" />
        )}
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-2xl bg-[hsl(var(--accent-50))] border border-[hsl(var(--accent-200))] flex items-center justify-center mb-4">
        <span className="text-2xl">💊</span>
      </div>
      <h2 className="text-lg font-semibold mb-2">medRAG — Doradca interakcji lekowych</h2>
      <p className="text-sm text-muted-foreground max-w-sm leading-relaxed">
        Zadaj pytanie o interakcje lekowe. Możesz wpisać nazwy leków, dawki lub objawy kliniczne.
      </p>
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg">
        {[
          "Jakie są interakcje między warfaryną a ibuprofenem?",
          "Czy metforminę można łączyć z inhibitorami ACE?",
          "Ryzyko przy jednoczesnym stosowaniu statyn i amiodaronu",
          "Interakcje leków przeciwdepresyjnych z SSRI",
        ].map((q) => (
          <button
            key={q}
            className="text-left text-xs px-3 py-2.5 rounded-lg border border-border hover:border-[hsl(var(--accent-300))] hover:bg-[hsl(var(--accent-50))] transition-colors text-muted-foreground hover:text-foreground"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

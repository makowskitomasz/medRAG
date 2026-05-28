"use client"

import { use, useEffect, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { conversationsApi } from "@/lib/api"
import { useChatStream } from "@/hooks/useChatStream"
import { useAppStore } from "@/store/app"
import { useTweaks } from "@/store/tweaks"
import { MessageBubble } from "@/components/chat/MessageBubble"
import { CitationsPanel } from "@/components/chat/CitationsPanel"
import { ChatInput } from "@/components/chat/ChatInput"
import { ModeSelector, type RagMode } from "@/components/chat/ModeSelector"
import { Topbar } from "@/components/layout/Topbar"
import { Skeleton } from "@/components/ui/skeleton"
import { useState } from "react"
import type { ChatMessage } from "@/hooks/useChatStream"

interface Props {
  params: Promise<{ id: string }>
}

export default function ConversationPage({ params }: Props) {
  const { id } = use(params)
  const { activeProjectId } = useAppStore()
  const { citationLayout } = useTweaks()
  const [ragMode, setRagMode] = useState<RagMode>("vanilla")

  const { data: conversation, isLoading } = useQuery({
    queryKey: ["conversation", id],
    queryFn: () => conversationsApi.get(id),
  })

  const { messages, phase, error, send, cancel } = useChatStream(
    conversation?.project_id ?? activeProjectId,
    id
  )

  // Pre-populate messages from history
  const [initialized, setInitialized] = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages])

  const allMessages: ChatMessage[] = conversation && !initialized
    ? [
        ...(conversation.messages ?? []).map((m) => ({
          id: `hist-${m.timestamp}-${m.role}`,
          role: m.role as "user" | "assistant",
          content: m.content,
        })),
        ...messages,
      ]
    : messages

  const lastMessage = allMessages[allMessages.length - 1]
  const lastCitations =
    lastMessage?.role === "assistant" ? (lastMessage.citations ?? []) : []
  const showSidebar = citationLayout === "sidebar" && lastCitations.length > 0

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Topbar title="Ładowanie…" />
        <div className="flex-1 p-6 space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-3/4" style={{ marginLeft: i % 2 === 0 ? "auto" : 0 }} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <Topbar title={conversation?.title ?? "Rozmowa"} />

      <div className="flex flex-1 min-h-0">
        <div className="flex flex-col flex-1 min-w-0">
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
            <div className="max-w-3xl mx-auto space-y-6">
              {allMessages.map((msg, i) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  isLast={i === allMessages.length - 1}
                  phase={phase}
                  citationLayout={citationLayout}
                  ragMode={ragMode}
                />
              ))}

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
            />
          </div>
        </div>

        {showSidebar && (
          <CitationsPanel citations={lastCitations} layout="sidebar" />
        )}
      </div>
    </div>
  )
}

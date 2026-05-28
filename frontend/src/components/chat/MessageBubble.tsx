"use client"

import { cn } from "@/lib/utils"
import type { ChatMessage } from "@/hooks/useChatStream"
import { ThinkingPanel } from "./ThinkingPanel"
import type { CitationLayout } from "@/store/tweaks"

interface Props {
  message: ChatMessage
  isLast: boolean
  phase: import("@/hooks/useChatStream").ChatPhase
  citationLayout: CitationLayout
  ragMode: string
}

export function MessageBubble({ message, isLast, phase, citationLayout, ragMode }: Props) {
  const isUser = message.role === "user"

  return (
    <div className={cn("flex gap-3", isUser && "justify-end")}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-[hsl(var(--accent-600))] flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">
          AI
        </div>
      )}

      <div className={cn("flex flex-col max-w-[80%]", isUser && "items-end")}>
        {/* Thinking panel — only shown while in flight on the last assistant message */}
        {!isUser && isLast && (phase === "searching" || phase === "thinking" || phase === "streaming") && (
          <ThinkingPanel
            phase={phase}
            searchEvents={message.searchEvents ?? []}
            thinkEvents={message.thinkEvents ?? []}
            ragMode={ragMode}
          />
        )}

        {/* Message content */}
        {(message.content || isUser) && (
          <div
            className={cn(
              "rounded-2xl px-4 py-2.5 text-sm",
              isUser
                ? "bg-[var(--message-user-bg)] text-[var(--message-user-fg)] rounded-tr-sm"
                : "bg-[var(--message-assistant-bg)] text-[var(--message-assistant-fg)] rounded-tl-sm w-full",
              !isUser && isLast && phase === "streaming" && "streaming-cursor"
            )}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <div
                className="prose"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
              />
            )}
          </div>
        )}

        {/* Citations (inline/cards — sidebar handled by parent) */}
        {!isUser && citationLayout !== "sidebar" && message.citations && message.citations.length > 0 && (
          <div className="mt-2 w-full">
            {/* Rendered by CitationsPanel in parent */}
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
          U
        </div>
      )}
    </div>
  )
}

// Minimal Markdown to HTML — for production use a proper library (marked, remark)
function renderMarkdown(text: string): string {
  if (!text) return ""
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    // Bold
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    // Italic
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    // Code inline
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    // Headers
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    // Lists
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>")
    // Citation markers [N]
    .replace(/\[(\d+)\]/g, '<span class="citation-marker">$1</span>')
    // Paragraphs
    .replace(/\n\n/g, "</p><p>")
    .replace(/^(?!<[hul])(.+)$/gm, "$1")
    .trim()
}

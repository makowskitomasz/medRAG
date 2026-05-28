"use client"

import { useRef } from "react"
import { Send, Square } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { ChatPhase } from "@/hooks/useChatStream"

interface Props {
  onSend: (query: string) => void
  onCancel: () => void
  phase: ChatPhase
  disabled?: boolean
}

export function ChatInput({ onSend, onCancel, phase, disabled }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const isInFlight = phase === "searching" || phase === "thinking" || phase === "streaming"

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function submit() {
    const value = textareaRef.current?.value.trim()
    if (!value || isInFlight) return
    onSend(value)
    if (textareaRef.current) textareaRef.current.value = ""
    resize()
  }

  function resize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }

  return (
    <div className="border-t border-border bg-background px-4 py-3">
      <div className="flex items-end gap-2 max-w-4xl mx-auto">
        <div className="flex-1 relative bg-muted/50 border border-border rounded-2xl transition-colors focus-within:border-[hsl(var(--accent-500))] focus-within:ring-1 focus-within:ring-[hsl(var(--accent-500))]">
          <textarea
            ref={textareaRef}
            rows={1}
            disabled={disabled}
            onKeyDown={handleKeyDown}
            onInput={resize}
            placeholder="Zapytaj o interakcje lekowe…"
            className={cn(
              "w-full resize-none bg-transparent px-4 py-3 text-sm outline-none placeholder:text-muted-foreground",
              "max-h-[200px] overflow-y-auto"
            )}
            style={{ height: "44px" }}
          />
        </div>

        {isInFlight ? (
          <Button
            type="button"
            variant="destructive"
            size="icon"
            onClick={onCancel}
            className="shrink-0 h-[44px] w-[44px] rounded-xl"
            aria-label="Zatrzymaj"
          >
            <Square className="h-4 w-4 fill-current" />
          </Button>
        ) : (
          <Button
            type="button"
            size="icon"
            onClick={submit}
            disabled={disabled}
            className="shrink-0 h-[44px] w-[44px] rounded-xl bg-[hsl(var(--accent-600))] hover:bg-[hsl(var(--accent-700))] text-white"
            aria-label="Wyślij"
          >
            <Send className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}

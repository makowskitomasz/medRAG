"use client";
import { useQuery } from "@tanstack/react-query";
import { conversations, ConversationSummary } from "@/lib/api";

export function useConversations(projectId: string | null) {
  return useQuery<ConversationSummary[]>({
    queryKey: ["conversations", projectId],
    queryFn: () => conversations.list(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

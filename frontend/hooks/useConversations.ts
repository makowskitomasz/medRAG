"use client";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { conversations, ConversationPage, ListConversationsParams } from "@/lib/api";

/** Recent conversations for the sidebar — one small page, never the whole history. */
export function useConversations(projectId: string | null, limit = 15) {
  return useQuery<ConversationPage>({
    queryKey: ["conversations", projectId, limit],
    queryFn: () => conversations.list({ projectId, limit }),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

/**
 * Paged history. The previous implementation fetched up to 100 conversations for
 * every project in parallel and filtered in the browser; search and filters now run
 * server-side and pages arrive on demand.
 */
export function useConversationHistory(params: Omit<ListConversationsParams, "page">) {
  return useInfiniteQuery<ConversationPage>({
    queryKey: ["conversation-history", params],
    queryFn: ({ pageParam }) =>
      conversations.list({ ...params, page: pageParam as number }),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page < last.pages ? last.page + 1 : undefined),
    staleTime: 30_000,
  });
}

export function useRenameConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      conversations.rename(id, title),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      qc.invalidateQueries({ queryKey: ["conversation-history"] });
    },
  });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => conversations.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      qc.invalidateQueries({ queryKey: ["conversation-history"] });
    },
  });
}

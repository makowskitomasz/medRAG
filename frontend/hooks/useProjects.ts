"use client";
import { useQuery, useQueries, useMutation, useQueryClient } from "@tanstack/react-query";
import { projects, documents, Project, SettingsOptions, UpdateSettingsInput, UpdateProjectInput } from "@/lib/api";

export function useProjects() {
  return useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: projects.list,
    staleTime: 60_000,
  });
}

export function useProjectStats(projectId: string | null) {
  return useQuery({
    queryKey: ["project-stats", projectId],
    queryFn: () => documents.projectStats(projectId!),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

/**
 * Indexed-document count per project id.
 *
 * Used to warn before a user asks an empty project a question, and to avoid
 * defaulting to one — the first project in the list is not necessarily usable.
 */
export function useProjectDocCounts(projectList: Project[]): Record<string, number> {
  const results = useQueries({
    queries: projectList.map((p) => ({
      queryKey: ["project-stats", p.project_id],
      queryFn: () => documents.projectStats(p.project_id),
      staleTime: 60_000,
    })),
  });
  const counts: Record<string, number> = {};
  projectList.forEach((p, i) => {
    const data = results[i]?.data;
    if (data) counts[p.project_id] = data.indexed_count ?? data.total_documents ?? 0;
  });
  return counts;
}

export function useProject(id: string | null) {
  return useQuery<Project>({
    queryKey: ["projects", id],
    queryFn: () => projects.get(id!),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useSettingsOptions() {
  return useQuery<SettingsOptions>({
    queryKey: ["settingsOptions"],
    queryFn: projects.getSettingsOptions,
    staleTime: Infinity,
  });
}

export function useUpdateSettings(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: UpdateSettingsInput) => projects.updateSettings(projectId, data),
    onSuccess: (updated) => {
      qc.setQueryData<Project[]>(["projects"], (old) =>
        old?.map((p) => (p.id === updated.id ? updated : p)) ?? [updated]
      );
      qc.setQueryData(["projects", projectId], updated);
    },
  });
}

export function useUpdateProject(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: UpdateProjectInput) => projects.update(projectId, data),
    onSuccess: (updated) => {
      qc.setQueryData<Project[]>(["projects"], (old) =>
        old?.map((p) => (p.id === updated.id ? updated : p)) ?? [updated]
      );
      qc.setQueryData(["projects", projectId], updated);
    },
  });
}

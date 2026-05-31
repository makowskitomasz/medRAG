"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { projects, Project, SettingsOptions, UpdateSettingsInput, UpdateProjectInput } from "@/lib/api";

export function useProjects() {
  return useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: projects.list,
    staleTime: 60_000,
  });
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

"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

interface AppState {
  activeProjectId: string | null
  sidebarCollapsed: boolean
  setActiveProject: (id: string | null) => void
  toggleSidebar: () => void
  setSidebarCollapsed: (v: boolean) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      activeProjectId: null,
      sidebarCollapsed: false,
      setActiveProject: (activeProjectId) => set({ activeProjectId }),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
    }),
    { name: "medrag-app" }
  )
)

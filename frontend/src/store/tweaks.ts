"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

export type Theme = "light" | "dark" | "system"
export type Accent = "blue" | "mint" | "navy" | "lavender"
export type Density = "comfortable" | "compact"
export type Font = "inter" | "geist" | "mono"
export type Anim = "normal" | "reduced"
export type CitationLayout = "sidebar" | "cards" | "inline"

interface TweaksState {
  theme: Theme
  accent: Accent
  density: Density
  font: Font
  anim: Anim
  citationLayout: CitationLayout
  setTheme: (t: Theme) => void
  setAccent: (a: Accent) => void
  setDensity: (d: Density) => void
  setFont: (f: Font) => void
  setAnim: (a: Anim) => void
  setCitationLayout: (l: CitationLayout) => void
}

export const useTweaks = create<TweaksState>()(
  persist(
    (set) => ({
      theme: "system",
      accent: "blue",
      density: "comfortable",
      font: "inter",
      anim: "normal",
      citationLayout: "sidebar",
      setTheme: (theme) => set({ theme }),
      setAccent: (accent) => set({ accent }),
      setDensity: (density) => set({ density }),
      setFont: (font) => set({ font }),
      setAnim: (anim) => set({ anim }),
      setCitationLayout: (citationLayout) => set({ citationLayout }),
    }),
    { name: "medrag-tweaks" }
  )
)

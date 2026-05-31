import { create } from "zustand";
import { persist } from "zustand/middleware";

type Locale = "en" | "pl";
type Theme = "light" | "dark";
type Accent = "blue" | "mint" | "navy" | "lavender";
type Density = "comfortable" | "compact";
type FontFamily = "inter" | "poppins" | "plex";
type AnimSpeed = "off" | "subtle" | "normal" | "playful";
type CitationLayout = "cards" | "sidebar" | "inline";
type RagMode =
  | "vanilla"
  | "hyde"
  | "query_rewriting"
  | "self_reflection"
  | "multi_agent"
  | "corrective_rag"
  | "iterative_multihop"
  | "madam_rag"
  | "rare_rag";

interface UIState {
  locale: Locale;
  theme: Theme;
  accent: Accent;
  density: Density;
  font: FontFamily;
  anim: AnimSpeed;
  citationLayout: CitationLayout;
  ragMode: RagMode;
  sidebarCollapsed: boolean;
  activeProjectId: string | null;
  setLocale: (l: Locale) => void;
  setTheme: (t: Theme) => void;
  setAccent: (a: Accent) => void;
  setDensity: (d: Density) => void;
  setFont: (f: FontFamily) => void;
  setAnim: (a: AnimSpeed) => void;
  setCitationLayout: (l: CitationLayout) => void;
  setRagMode: (m: RagMode) => void;
  setSidebarCollapsed: (v: boolean) => void;
  setActiveProjectId: (id: string | null) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      locale: "en",
      theme: "light",
      accent: "blue",
      density: "comfortable",
      font: "inter",
      anim: "normal",
      citationLayout: "cards",
      ragMode: "vanilla",
      sidebarCollapsed: false,
      activeProjectId: null,
      setLocale: (locale) => set({ locale }),
      setTheme: (theme) => set({ theme }),
      setAccent: (accent) => set({ accent }),
      setDensity: (density) => set({ density }),
      setFont: (font) => set({ font }),
      setAnim: (anim) => set({ anim }),
      setCitationLayout: (citationLayout) => set({ citationLayout }),
      setRagMode: (ragMode) => set({ ragMode }),
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
      setActiveProjectId: (activeProjectId) => set({ activeProjectId }),
    }),
    { name: "medrag-ui" }
  )
);

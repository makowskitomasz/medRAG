"use client"

import { useEffect } from "react"
import { useTweaks } from "@/store/tweaks"

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { theme, accent, density, font, anim } = useTweaks()

  useEffect(() => {
    const html = document.documentElement
    const resolvedTheme =
      theme === "system"
        ? window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light"
        : theme

    html.dataset.theme = resolvedTheme
    html.dataset.accent = accent
    html.dataset.density = density
    html.dataset.font = font
    html.dataset.anim = anim
  }, [theme, accent, density, font, anim])

  // watch system preference changes
  useEffect(() => {
    if (theme !== "system") return
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = () => {
      document.documentElement.dataset.theme = mq.matches ? "dark" : "light"
    }
    mq.addEventListener("change", handler)
    return () => mq.removeEventListener("change", handler)
  }, [theme])

  return <>{children}</>
}

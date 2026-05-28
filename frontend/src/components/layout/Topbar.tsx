"use client"

import { useQuery } from "@tanstack/react-query"
import { Sun, Moon, Monitor, Palette } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu"
import { useTweaks, type Theme, type Accent } from "@/store/tweaks"
import { useAppStore } from "@/store/app"
import { projectsApi } from "@/lib/api"

export function Topbar({ title }: { title?: string }) {
  const { theme, accent, setTheme, setAccent } = useTweaks()
  const { activeProjectId, setActiveProject } = useAppStore()

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list(),
  })

  return (
    <header className="h-14 border-b border-border flex items-center px-4 gap-3 shrink-0 bg-background/80 backdrop-blur-sm">
      <div className="flex-1 min-w-0">
        {title && <h1 className="text-sm font-medium truncate">{title}</h1>}
      </div>

      {/* Project selector */}
      {projects && projects.length > 0 && (
        <DropdownMenu>
          <DropdownMenuTrigger>
            <Button variant="outline" size="sm" className="gap-1.5 max-w-[180px] truncate">
              <span className="truncate">
                {projects.find((p) => p.project_id === activeProjectId)?.name ?? "Wybierz projekt"}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Projekty</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {projects.map((p) => (
              <DropdownMenuItem
                key={p.project_id}
                onSelect={() => setActiveProject(p.project_id)}
                className={activeProjectId === p.project_id ? "font-medium" : ""}
              >
                {p.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}

      {/* Theme toggle */}
      <DropdownMenu>
        <DropdownMenuTrigger>
          <Button variant="ghost" size="icon" aria-label="Zmień motyw">
            {theme === "dark" ? <Moon className="h-4 w-4" /> : theme === "light" ? <Sun className="h-4 w-4" /> : <Monitor className="h-4 w-4" />}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Motyw</DropdownMenuLabel>
          <DropdownMenuRadioGroup value={theme} onValueChange={(v) => setTheme(v as Theme)}>
            <DropdownMenuRadioItem value="light"><Sun className="h-3.5 w-3.5 mr-2" />Jasny</DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="dark"><Moon className="h-3.5 w-3.5 mr-2" />Ciemny</DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="system"><Monitor className="h-3.5 w-3.5 mr-2" />Systemowy</DropdownMenuRadioItem>
          </DropdownMenuRadioGroup>
          <DropdownMenuSeparator />
          <DropdownMenuLabel>Akcent</DropdownMenuLabel>
          <DropdownMenuRadioGroup value={accent} onValueChange={(v) => setAccent(v as Accent)}>
            <DropdownMenuRadioItem value="blue">Niebieski</DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="mint">Miętowy</DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="navy">Granatowy</DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="lavender">Lawendowy</DropdownMenuRadioItem>
          </DropdownMenuRadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}

"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import {
  MessageSquare,
  History,
  Settings,
  ChevronLeft,
  ChevronRight,
  Plus,
  FlaskConical,
  LogOut,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAppStore } from "@/store/app"
import { conversationsApi, type ConversationSummary } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { authApi } from "@/lib/api"
import { toast } from "sonner"

const NAV = [
  { href: "/chat", icon: MessageSquare, label: "Nowa rozmowa" },
  { href: "/history", icon: History, label: "Historia" },
  { href: "/admin", icon: Settings, label: "Admin" },
]

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { sidebarCollapsed, toggleSidebar, activeProjectId } = useAppStore()

  const { data: conversations } = useQuery({
    queryKey: ["conversations", activeProjectId],
    queryFn: () => conversationsApi.list(activeProjectId ?? undefined),
    enabled: !sidebarCollapsed,
  })

  async function handleLogout() {
    await authApi.logout()
    router.push("/login")
    router.refresh()
  }

  const width = sidebarCollapsed ? "w-14" : "w-[260px]"

  return (
    <aside
      className={cn(
        "flex flex-col h-full border-r border-border bg-[hsl(var(--sidebar-bg))] shrink-0 transition-[width] duration-200",
        width
      )}
    >
      {/* Logo + collapse */}
      <div className="flex items-center h-14 px-3 border-b border-border shrink-0">
        {!sidebarCollapsed && (
          <Link href="/chat" className="flex items-center gap-2 flex-1 min-w-0">
            <div className="w-7 h-7 rounded-md bg-[hsl(var(--accent-600))] flex items-center justify-center text-white font-bold text-sm shrink-0">
              M
            </div>
            <span className="font-semibold text-sm tracking-tight truncate">medRAG</span>
          </Link>
        )}
        {sidebarCollapsed && (
          <div className="w-7 h-7 rounded-md bg-[hsl(var(--accent-600))] flex items-center justify-center text-white font-bold text-sm mx-auto">
            M
          </div>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className={cn("shrink-0 h-7 w-7", sidebarCollapsed && "mx-auto mt-2")}
          aria-label="Toggle sidebar"
        >
          {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>

      {/* Nav */}
      <nav className="px-2 pt-3 space-y-0.5">
        {NAV.map(({ href, icon: Icon, label }) => (
          <NavItem
            key={href}
            href={href}
            icon={Icon}
            label={label}
            collapsed={sidebarCollapsed}
            active={pathname === href || (href !== "/chat" && pathname.startsWith(href))}
          />
        ))}

        <div className="pt-2">
          <NavItem
            href="/chat"
            icon={Plus}
            label="Nowa rozmowa"
            collapsed={sidebarCollapsed}
            active={false}
            variant="accent"
          />
        </div>
      </nav>

      {/* Recent conversations */}
      {!sidebarCollapsed && conversations && conversations.length > 0 && (
        <div className="flex-1 min-h-0 mt-4">
          <p className="px-3 text-xs font-medium text-muted-foreground mb-1.5">Ostatnie rozmowy</p>
          <ScrollArea className="h-full">
            <div className="px-2 space-y-0.5 pb-2">
              {conversations.slice(0, 20).map((conv) => (
                <Link
                  key={conv.id}
                  href={`/chat/${conv.id}`}
                  className={cn(
                    "flex items-center gap-2 px-2 py-1.5 rounded-md text-sm truncate hover:bg-muted transition-colors",
                    pathname === `/chat/${conv.id}` && "bg-muted font-medium"
                  )}
                >
                  <FlaskConical className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="truncate">{conv.title ?? "Nowa rozmowa"}</span>
                </Link>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Logout */}
      <div className="px-2 pb-3 pt-2 border-t border-border">
        {sidebarCollapsed ? (
          <Tooltip>
            <TooltipTrigger>
              <Button variant="ghost" size="icon" onClick={handleLogout} className="w-full h-9">
                <LogOut className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">Wyloguj</TooltipContent>
          </Tooltip>
        ) : (
          <Button variant="ghost" className="w-full justify-start gap-2 h-9 text-sm" onClick={handleLogout}>
            <LogOut className="h-4 w-4" />
            Wyloguj
          </Button>
        )}
      </div>
    </aside>
  )
}

function NavItem({
  href,
  icon: Icon,
  label,
  collapsed,
  active,
  variant = "default",
}: {
  href: string
  icon: React.ElementType
  label: string
  collapsed: boolean
  active: boolean
  variant?: "default" | "accent"
}) {
  const btn = (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-2.5 px-2 py-2 rounded-md text-sm transition-colors",
        collapsed && "justify-center px-0",
        active && "bg-muted font-medium text-foreground",
        !active && variant === "default" && "text-muted-foreground hover:text-foreground hover:bg-muted",
        variant === "accent" && "text-[hsl(var(--accent-600))] hover:bg-[hsl(var(--accent-50))]"
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </Link>
  )

  if (!collapsed) return btn

  return (
    <Tooltip>
      <TooltipTrigger>{btn}</TooltipTrigger>
      <TooltipContent side="right">{label}</TooltipContent>
    </Tooltip>
  )
}

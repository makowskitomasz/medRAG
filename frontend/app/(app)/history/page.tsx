"use client";
export const dynamic = "force-dynamic";
import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  ChevronRight, Search, X, Sparkles, MoreHorizontal, ExternalLink, Link,
} from "lucide-react";
import { conversations, projects, auth, ConversationSummary } from "@/lib/api";
import { useUIStore } from "@/store";
import { getUser } from "@/lib/auth";

const MODE_LABELS: Record<string, string> = {
  vanilla: "Vanilla",
  hyde: "HyDE",
  query_rewriting: "Rewriting",
  self_reflection: "Reflect",
  multi_agent: "Multi",
  corrective_rag: "CRAG",
  iterative_multihop: "MultiHop",
  madam_rag: "MADAM",
  rare_rag: "RARE",
};

type StoredUser = { id?: string; email: string; role: string; first_name?: string | null; last_name?: string | null };

export default function HistoryPage() {
  const router = useRouter();
  const { setActiveProjectId } = useUIStore();
  const currentUser = getUser<StoredUser>();
  const isAdmin = currentUser?.role === "admin";
  const [query, setQuery] = useState("");
  const [filterProjectId, setFilterProjectId] = useState("all");
  const [filterMode, setFilterMode] = useState("all");
  const [view, setView] = useState<"list" | "grid">("list");
  const [menu, setMenu] = useState<{ id: string; top: number; right: number } | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const t = useTranslations("history");

  useEffect(() => {
    if (!menu) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenu(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menu]);

  const openMenu = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (menu?.id === id) { setMenu(null); return; }
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setMenu({ id, top: rect.bottom + 6, right: window.innerWidth - rect.right });
  };

  const { data: projectList = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: projects.list,
  });

  const { data: allUsers = [] } = useQuery({
    queryKey: ["users"],
    queryFn: auth.listUsers,
    enabled: isAdmin,
    staleTime: 60_000,
  });

  const userDisplayName = (userId: string | null) => {
    if (!userId) return null;
    const u = allUsers.find((x) => x.id === userId);
    if (!u) return userId.slice(-6);
    const full = [u.first_name, u.last_name].filter(Boolean).join(" ");
    return full || u.email;
  };

  const userInitials = (userId: string | null) => {
    if (!userId) return "?";
    const u = allUsers.find((x) => x.id === userId);
    if (!u) return "?";
    if (u.first_name) return (u.first_name[0] + (u.last_name?.[0] ?? "")).toUpperCase();
    return u.email.slice(0, 2).toUpperCase();
  };

  const { data: allConvs = [], isLoading } = useQuery<ConversationSummary[]>({
    queryKey: ["all-conversations", projectList.map((p) => p.id).join(",")],
    queryFn: async () => {
      const results = await Promise.all(
        projectList.map((p) => conversations.list(p.id, 100))
      );
      return results.flat();
    },
    enabled: projectList.length > 0,
    staleTime: 30_000,
  });

  const filtered = allConvs.filter((c) => {
    if (filterProjectId !== "all" && c.project_id !== filterProjectId) return false;
    if (filterMode !== "all" && c.rag_mode !== filterMode) return false;
    const title = c.first_user_message ?? "";
    if (query && !title.toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  });

  const projectName = (id: string) =>
    projectList.find((p) => p.id === id)?.name ?? id;
  const projectColor = (id: string) =>
    projectList.find((p) => p.id === id)?.color ?? "#7DD3FC";
  const projectInitials = (id: string) =>
    projectList.find((p) => p.id === id)?.initials ?? id.slice(-2).toUpperCase();
  const formatTime = (iso: string) => {
    const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  };

  const openConversation = (c: ConversationSummary) => {
    setActiveProjectId(c.project_id);
    router.push(`/chat/${c.id}`);
  };

  const copyLink = (id: string) => {
    navigator.clipboard.writeText(`${window.location.origin}/chat/${id}`);
    setMenu(null);
  };

  return (
    <>
    <div className="hist-root fade-in">
      <div className="hist-header">
        <div className="hist-header-l">
          <button className="btn-ghost hist-back" onClick={() => router.back()}>
            <ChevronRight size={14} style={{ transform: "rotate(180deg)" }} />
            {t("backToChat")}
          </button>
          <h1>{t("title")}</h1>
          <p>{isLoading ? t("loading") : t("subtitle", { n: allConvs.length, p: projectList.length })}</p>
        </div>
        <div className="hist-header-r">
          <div className="hist-view-toggle">
            <button className={view === "list" ? "hist-view-active" : ""} onClick={() => setView("list")}>{t("listView")}</button>
            <button className={view === "grid" ? "hist-view-active" : ""} onClick={() => setView("grid")}>{t("gridView")}</button>
          </div>
        </div>
      </div>

      <div className="hist-toolbar">
        <div className="hist-search">
          <Search size={15} />
          <input placeholder={t("searchPlaceholder")} value={query} onChange={(e) => setQuery(e.target.value)} />
          {query && (
            <button className="icon-btn hist-clear" onClick={() => setQuery("")}><X size={13} /></button>
          )}
        </div>
        <div className="hist-filters">
          <div className="hist-filter">
            <select value={filterProjectId} onChange={(e) => setFilterProjectId(e.target.value)}>
              <option value="all">{t("allProjects")}</option>
              {projectList.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div className="hist-filter">
            <Sparkles size={12} />
            <select value={filterMode} onChange={(e) => setFilterMode(e.target.value)}>
              <option value="all">{t("allModes")}</option>
              <option value="vanilla">Vanilla</option>
              <option value="hyde">HyDE</option>
              <option value="self_reflection">Reflect</option>
              <option value="multi_agent">Multi-Agent</option>
            </select>
          </div>
        </div>
      </div>

      <div className={`hist-results hist-results-${view}`}>
        {isLoading && (
          <div className="hist-empty">
            <div className="search-spinner" style={{ margin: "0 auto" }} />
            <p style={{ marginTop: 12 }}>{t("loading")}</p>
          </div>
        )}
        {!isLoading && filtered.length === 0 && (
          <div className="hist-empty">
            <Search size={32} />
            <p>{query ? t("noResults", { q: query }) : t("noConversations")}</p>
            <button className="btn-ghost" onClick={() => { setQuery(""); setFilterMode("all"); setFilterProjectId("all"); }}>
              {t("clearFilters")}
            </button>
          </div>
        )}
        {!isLoading && view === "list" && filtered.length > 0 && (
          <div className="hist-list stagger">
            {filtered.map((c) => (
              <div key={c.id} className="hist-row" onClick={() => openConversation(c)} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && openConversation(c)}>
                <div className="hist-row-l">
                  <span className="hist-row-title">{c.first_user_message ?? `Conversation ${c.id.slice(-6)}`}</span>
                </div>
                <div className="hist-row-meta">
                  <span className="hist-row-proj" style={{ background: projectColor(c.project_id) + "20", color: projectColor(c.project_id) }}>
                    {projectInitials(c.project_id)}
                  </span>
                  <span className="hist-row-proj-name">{projectName(c.project_id)}</span>
                  <span className="hist-row-mode"><Sparkles size={11} />{MODE_LABELS[c.rag_mode] ?? c.rag_mode}</span>
                  <span className="hist-row-time">{formatTime(c.updated_at)}</span>
                  {isAdmin && c.user_id && (
                    <span className="hist-row-owner" title={userDisplayName(c.user_id) ?? undefined}>
                      {userInitials(c.user_id)}
                    </span>
                  )}
                  <button className="icon-btn hist-row-more" onClick={(e) => openMenu(e, c.id)}>
                    <MoreHorizontal size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        {!isLoading && view === "grid" && filtered.length > 0 && (
          <div className="hist-grid stagger">
            {filtered.map((c) => (
              <button key={c.id} className="hist-card" onClick={() => openConversation(c)}>
                <div className="hist-card-head">
                  <span className="hist-row-proj" style={{ background: projectColor(c.project_id) + "20", color: projectColor(c.project_id) }}>
                    {projectInitials(c.project_id)}
                  </span>
                  <span className="hist-row-time" style={{ marginLeft: "auto" }}>{formatTime(c.updated_at)}</span>
                </div>
                <div className="hist-card-title">{c.first_user_message ?? `Conversation ${c.id.slice(-6)}`}</div>
                <div className="hist-card-foot">
                  <span className="hist-row-mode"><Sparkles size={11} />{MODE_LABELS[c.rag_mode] ?? c.rag_mode}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span className="hist-card-proj-name">{projectName(c.project_id)}</span>
                    {isAdmin && c.user_id && (
                      <span className="hist-row-owner" title={userDisplayName(c.user_id) ?? undefined}>
                        {userInitials(c.user_id)}
                      </span>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>

    {menu && createPortal(
      <div
        ref={menuRef}
        className="hist-row-menu"
        style={{ position: "fixed", top: menu.top, right: menu.right }}
      >
        <button onClick={(e) => { e.stopPropagation(); const c = filtered.find((x) => x.id === menu.id)!; setMenu(null); openConversation(c); }}>
          <ExternalLink size={13} /> Open
        </button>
        <button onClick={(e) => { e.stopPropagation(); copyLink(menu.id); }}>
          <Link size={13} /> Copy link
        </button>
      </div>,
      document.body
    )}
    </>
  );
}

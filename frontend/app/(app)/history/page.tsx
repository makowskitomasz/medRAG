"use client";
export const dynamic = "force-dynamic";
import { useState, useRef, useEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTranslations, useLocale } from "next-intl";
import {
  ChevronRight, Search, X, Sparkles, MoreHorizontal, ExternalLink, Link,
  Pencil, Trash2, Check,
} from "lucide-react";
import { projects, auth, ConversationSummary, conversationLabel } from "@/lib/api";
import {
  useConversationHistory,
  useRenameConversation,
  useDeleteConversation,
} from "@/hooks/useConversations";
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

/** Keeps the server query one step behind the keystrokes. */
function useDebounced<T>(value: T, ms = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return debounced;
}

export default function HistoryPage() {
  const router = useRouter();
  const locale = useLocale();
  const { setActiveProjectId } = useUIStore();
  const currentUser = getUser<StoredUser>();
  const isAdmin = currentUser?.role === "admin";
  const [query, setQuery] = useState("");
  const [filterProjectId, setFilterProjectId] = useState("all");
  const [filterMode, setFilterMode] = useState("all");
  const [view, setView] = useState<"list" | "grid">("list");
  const [menu, setMenu] = useState<{ id: string; top: number; right: number } | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const t = useTranslations("history");

  const debouncedQuery = useDebounced(query);

  useEffect(() => {
    if (!menu) return;
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenu(null);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setMenu(null); };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
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

  // Search, project and mode filters all run server-side; pages arrive on demand
  // rather than pulling every conversation of every project up front.
  const {
    data,
    isLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useConversationHistory({
    projectId: filterProjectId === "all" ? undefined : filterProjectId,
    q: debouncedQuery || undefined,
    ragMode: filterMode,
    limit: 25,
  });

  const rename = useRenameConversation();
  const remove = useDeleteConversation();

  const items = useMemo(
    () => (data?.pages ?? []).flatMap((p) => p.items),
    [data]
  );
  const total = data?.pages[0]?.total ?? 0;

  const userDisplayName = (userId: string | null) => {
    if (!userId) return null;
    const u = allUsers.find((x) => x.id === userId);
    if (!u) return userId.slice(-6);
    return [u.first_name, u.last_name].filter(Boolean).join(" ") || u.email;
  };

  const userInitials = (userId: string | null) => {
    if (!userId) return "?";
    const u = allUsers.find((x) => x.id === userId);
    if (!u) return "?";
    if (u.first_name) return (u.first_name[0] + (u.last_name?.[0] ?? "")).toUpperCase();
    return u.email.slice(0, 2).toUpperCase();
  };

  const projectName = (id: string) => projectList.find((p) => p.id === id)?.name ?? id;
  const projectColor = (id: string) => projectList.find((p) => p.id === id)?.color ?? "#7DD3FC";
  const projectInitials = (id: string) =>
    projectList.find((p) => p.id === id)?.initials ?? id.slice(-2).toUpperCase();

  const formatTime = (iso: string) => {
    const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
    return d.toLocaleDateString(locale, {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
  };

  const openConversation = (c: ConversationSummary) => {
    setActiveProjectId(c.project_id);
    router.push(`/chat/${c.id}`);
  };

  const copyLink = (id: string) => {
    navigator.clipboard.writeText(`${window.location.origin}/chat/${id}`).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 1500);
    }).catch(() => {});
    setMenu(null);
  };

  const startRename = (c: ConversationSummary) => {
    setMenu(null);
    setRenamingId(c.id);
    setRenameDraft(conversationLabel(c));
  };

  const commitRename = (id: string) => {
    const title = renameDraft.trim();
    setRenamingId(null);
    if (title) rename.mutate({ id, title });
  };

  const handleDelete = (c: ConversationSummary) => {
    setMenu(null);
    if (confirm(t("deleteConfirm", { name: conversationLabel(c) }))) remove.mutate(c.id);
  };

  const clearFilters = () => {
    setQuery("");
    setFilterMode("all");
    setFilterProjectId("all");
  };

  const menuTarget = items.find((x) => x.id === menu?.id);

  return (
    <>
    <div className="hist-root fade-in">
      <div className="hist-header">
        <div className="hist-header-l">
          <button className="btn-ghost hist-back" onClick={() => router.back()}>
            <ChevronRight size={14} style={{ transform: "rotate(180deg)" }} aria-hidden="true" />
            {t("backToChat")}
          </button>
          <h1>{t("title")}</h1>
          <p>{isLoading ? t("loading") : t("subtitle", { n: total, p: projectList.length })}</p>
        </div>
        <div className="hist-header-r">
          <div className="hist-view-toggle" role="group" aria-label="View">
            <button
              className={view === "list" ? "hist-view-active" : ""}
              aria-pressed={view === "list"}
              onClick={() => setView("list")}
            >{t("listView")}</button>
            <button
              className={view === "grid" ? "hist-view-active" : ""}
              aria-pressed={view === "grid"}
              onClick={() => setView("grid")}
            >{t("gridView")}</button>
          </div>
        </div>
      </div>

      <div className="hist-toolbar">
        <div className="hist-search">
          <Search size={15} aria-hidden="true" />
          <input
            placeholder={t("searchPlaceholder")}
            aria-label={t("searchPlaceholder")}
            title={t("searchHint")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button className="icon-btn hist-clear" onClick={() => setQuery("")} aria-label="Clear search">
              <X size={13} />
            </button>
          )}
        </div>
        <div className="hist-filters">
          <div className="hist-filter">
            <select
              value={filterProjectId}
              aria-label={t("allProjects")}
              onChange={(e) => setFilterProjectId(e.target.value)}
            >
              <option value="all">{t("allProjects")}</option>
              {projectList.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div className="hist-filter">
            <Sparkles size={12} aria-hidden="true" />
            <select
              value={filterMode}
              aria-label={t("allModes")}
              onChange={(e) => setFilterMode(e.target.value)}
            >
              <option value="all">{t("allModes")}</option>
              {Object.entries(MODE_LABELS).map(([id, label]) => (
                <option key={id} value={id}>{label}</option>
              ))}
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
        {!isLoading && items.length === 0 && (
          <div className="hist-empty">
            <Search size={32} aria-hidden="true" />
            <p>{query ? t("noResults", { q: query }) : t("noConversations")}</p>
            <button className="btn-ghost" onClick={clearFilters}>{t("clearFilters")}</button>
          </div>
        )}

        {!isLoading && view === "list" && items.length > 0 && (
          <div className="hist-list stagger">
            {items.map((c) => (
              <div
                key={c.id}
                className="hist-row"
                onClick={() => renamingId !== c.id && openConversation(c)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && renamingId !== c.id && openConversation(c)}
              >
                <div className="hist-row-l">
                  {renamingId === c.id ? (
                    <input
                      className="hist-rename-input"
                      autoFocus
                      value={renameDraft}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => setRenameDraft(e.target.value)}
                      onBlur={() => commitRename(c.id)}
                      onKeyDown={(e) => {
                        e.stopPropagation();
                        if (e.key === "Enter") commitRename(c.id);
                        if (e.key === "Escape") setRenamingId(null);
                      }}
                    />
                  ) : (
                    <>
                      <span className="hist-row-title">{conversationLabel(c)}</span>
                      {c.last_message_preview && (
                        <span className="hist-row-preview">{c.last_message_preview}</span>
                      )}
                    </>
                  )}
                </div>
                <div className="hist-row-meta">
                  <span className="hist-row-proj" style={{ background: projectColor(c.project_id) + "20", color: projectColor(c.project_id) }}>
                    {projectInitials(c.project_id)}
                  </span>
                  <span className="hist-row-proj-name">{projectName(c.project_id)}</span>
                  <span className="hist-row-mode"><Sparkles size={11} aria-hidden="true" />{MODE_LABELS[c.rag_mode] ?? c.rag_mode}</span>
                  <span className="hist-row-time">{formatTime(c.updated_at)}</span>
                  {isAdmin && c.user_id && (
                    <span className="hist-row-owner" title={userDisplayName(c.user_id) ?? undefined}>
                      {userInitials(c.user_id)}
                    </span>
                  )}
                  <button
                    className="icon-btn hist-row-more"
                    onClick={(e) => openMenu(e, c.id)}
                    aria-label={t("open")}
                    aria-haspopup="menu"
                    aria-expanded={menu?.id === c.id}
                  >
                    {copiedId === c.id ? <Check size={14} /> : <MoreHorizontal size={14} />}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && view === "grid" && items.length > 0 && (
          <div className="hist-grid stagger">
            {items.map((c) => (
              <button key={c.id} className="hist-card" onClick={() => openConversation(c)}>
                <div className="hist-card-head">
                  <span className="hist-row-proj" style={{ background: projectColor(c.project_id) + "20", color: projectColor(c.project_id) }}>
                    {projectInitials(c.project_id)}
                  </span>
                  <span className="hist-row-time" style={{ marginLeft: "auto" }}>{formatTime(c.updated_at)}</span>
                </div>
                <div className="hist-card-title">{conversationLabel(c)}</div>
                {c.last_message_preview && (
                  <div className="hist-card-preview">{c.last_message_preview}</div>
                )}
                <div className="hist-card-foot">
                  <span className="hist-row-mode"><Sparkles size={11} aria-hidden="true" />{MODE_LABELS[c.rag_mode] ?? c.rag_mode}</span>
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

        {!isLoading && items.length > 0 && (
          <div className="hist-more">
            <span className="hist-more-count">{t("showingCount", { n: items.length, total })}</span>
            {hasNextPage ? (
              <button
                className="btn-ghost"
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? t("loadingMore") : t("loadMore")}
              </button>
            ) : (
              <span className="hist-more-end">{t("endOfList")}</span>
            )}
          </div>
        )}
      </div>
    </div>

    {menu && menuTarget && createPortal(
      <div
        ref={menuRef}
        className="hist-row-menu"
        role="menu"
        style={{ position: "fixed", top: menu.top, right: menu.right }}
      >
        <button role="menuitem" onClick={(e) => { e.stopPropagation(); setMenu(null); openConversation(menuTarget); }}>
          <ExternalLink size={13} /> {t("open")}
        </button>
        <button role="menuitem" onClick={(e) => { e.stopPropagation(); copyLink(menu.id); }}>
          <Link size={13} /> {t("copyLink")}
        </button>
        <button role="menuitem" onClick={(e) => { e.stopPropagation(); startRename(menuTarget); }}>
          <Pencil size={13} /> {t("rename")}
        </button>
        <button role="menuitem" className="hist-row-menu-danger" onClick={(e) => { e.stopPropagation(); handleDelete(menuTarget); }}>
          <Trash2 size={13} /> {t("delete")}
        </button>
      </div>,
      document.body
    )}
    </>
  );
}

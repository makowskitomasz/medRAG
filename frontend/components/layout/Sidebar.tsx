"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Activity, ChevronRight, ChevronDown, Plus, Search, Settings, LogOut, User,
  MoreHorizontal, Pencil, Trash2, Columns2, X, AlertCircle,
} from "lucide-react";
import { useUIStore } from "@/store";
import { useProjects, useProjectDocCounts } from "@/hooks/useProjects";
import {
  useConversations,
  useRenameConversation,
  useDeleteConversation,
} from "@/hooks/useConversations";
import { auth, Project, conversationLabel } from "@/lib/api";
import { clearAuth, getUser, saveUser } from "@/lib/auth";
import { useQueryClient } from "@tanstack/react-query";

/** Closes a popup on an outside click or Escape — menus had neither before. */
function useDismissable(
  ref: React.RefObject<HTMLDivElement | null>,
  isOpen: boolean,
  close: () => void
) {
  useEffect(() => {
    if (!isOpen) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [isOpen, ref, close]);
}

interface Props {
  onNewChat: () => void;
  activeConvTitle?: string;
  activeConvId?: string;
  /** Mobile only — the sidebar renders as an off-canvas drawer below 900px. */
  mobileOpen?: boolean;
  onMobileClose?: () => void;
  onSettingsOpen?: () => void;
}

export default function Sidebar({
  onNewChat, activeConvTitle, activeConvId, mobileOpen, onMobileClose, onSettingsOpen,
}: Props) {
  const router = useRouter();
  const t = useTranslations("sidebar");
  const tTop = useTranslations("topbar");
  const { sidebarCollapsed, setSidebarCollapsed, activeProjectId, setActiveProjectId } = useUIStore();
  const qc = useQueryClient();
  const [showProjMenu, setShowProjMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [search, setSearch] = useState("");
  const [convMenuId, setConvMenuId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const userMenuRef = useRef<HTMLDivElement>(null);
  const projMenuRef = useRef<HTMLDivElement>(null);
  const convMenuRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const { data: projectList = [] } = useProjects();
  const docCounts = useProjectDocCounts(projectList);
  const { data: convPage } = useConversations(activeProjectId);
  const convList = convPage?.items ?? [];
  const rename = useRenameConversation();
  const remove = useDeleteConversation();

  useDismissable(userMenuRef, showUserMenu, useCallback(() => setShowUserMenu(false), []));
  useDismissable(projMenuRef, showProjMenu, useCallback(() => setShowProjMenu(false), []));
  useDismissable(convMenuRef, convMenuId !== null, useCallback(() => setConvMenuId(null), []));

  // ⌘K / Ctrl+K was advertised on the search field but never wired up.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSidebarCollapsed(false);
        requestAnimationFrame(() => searchRef.current?.focus());
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setSidebarCollapsed]);

  // Default to a project that actually has documents — picking the first one
  // silently sent a user's first question to an empty index.
  useEffect(() => {
    if (activeProjectId || projectList.length === 0) return;
    const withDocs = projectList.find((p) => (docCounts[p.project_id] ?? 0) > 0);
    setActiveProjectId((withDocs ?? projectList[0]).project_id);
  }, [activeProjectId, projectList, docCounts, setActiveProjectId]);

  type StoredUser = { email: string; role: string; first_name?: string | null; last_name?: string | null };
  const [user, setUser] = useState<StoredUser | null>(null);
  useEffect(() => {
    setUser(getUser<StoredUser>());
    auth.me().then((fresh) => { saveUser(fresh); setUser(fresh as StoredUser); }).catch(() => {});
  }, []);
  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.email || "User";
  const avatarText = user?.first_name
    ? (user.first_name[0] + (user.last_name?.[0] ?? "")).toUpperCase()
    : (user?.email?.slice(0, 2).toUpperCase() ?? "?");
  const activeProject = projectList.find((p) => p.project_id === activeProjectId) ?? projectList[0];

  const filteredConvs = convList.filter((c) =>
    !search || conversationLabel(c).toLowerCase().includes(search.toLowerCase())
  );

  const initials = (p: Project) => p.initials ?? p.name.slice(0, 2).toUpperCase();
  const docLabel = (p: Project) => {
    const n = docCounts[p.project_id];
    if (n === undefined) return p.description || "—";
    return n === 0 ? t("noDocuments") : t("docsCount", { n });
  };

  const handleLogout = () => {
    clearAuth();
    qc.clear();
    router.replace("/login");
  };

  const startRename = (id: string, current: string) => {
    setConvMenuId(null);
    setRenamingId(id);
    setRenameDraft(current);
  };

  const commitRename = (id: string) => {
    const title = renameDraft.trim();
    setRenamingId(null);
    if (title) rename.mutate({ id, title });
  };

  const handleDelete = (id: string, name: string) => {
    setConvMenuId(null);
    if (!confirm(t("deleteConfirm", { name }))) return;
    remove.mutate(id, {
      onSuccess: () => { if (activeConvId === id) onNewChat(); },
    });
  };

  const go = (path: string) => { onMobileClose?.(); router.push(path); };

  return (
    <>
      {mobileOpen && <div className="chat-sb-scrim" onClick={onMobileClose} aria-hidden="true" />}
      <aside
        className={`chat-sidebar${sidebarCollapsed ? " chat-sidebar-collapsed" : ""}${mobileOpen ? " chat-sidebar-mobile-open" : ""}`}
        aria-label="Conversations"
      >
        <div className="chat-sb-head">
          <button className="chat-sb-logo" onClick={() => go("/chat/new")}>
            <Activity size={22} aria-hidden="true" />
            {!sidebarCollapsed && <span>medRAG</span>}
          </button>
          <button
            className="icon-btn chat-sb-collapse"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            title={sidebarCollapsed ? "Expand" : "Collapse"}
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!sidebarCollapsed}
          >
            <ChevronRight size={14} style={{ transform: sidebarCollapsed ? "" : "rotate(180deg)" }} />
          </button>
          <button
            className="icon-btn chat-sb-mobile-close"
            onClick={onMobileClose}
            aria-label={t("closeSidebar")}
          >
            <X size={16} />
          </button>
        </div>

        {!sidebarCollapsed && (
          <>
            {!activeProject && user?.role === "admin" && (
              <div style={{ padding: "10px 12px" }}>
                <button
                  className="chat-sb-proj-mng"
                  style={{ width: "100%", justifyContent: "center", padding: "8px 12px" }}
                  onClick={() => go("/admin")}
                >
                  <Settings size={13} />
                  {t("manageProjects")}
                </button>
              </div>
            )}

            {activeProject && (
              <div className="chat-sb-project" ref={projMenuRef}>
                <button
                  className="chat-sb-proj-btn"
                  onClick={() => setShowProjMenu(!showProjMenu)}
                  aria-expanded={showProjMenu}
                  aria-haspopup="menu"
                >
                  <span
                    className="chat-sb-proj-init"
                    style={{ background: (activeProject.color ?? "#7DD3FC") + "30", color: activeProject.color ?? "#7DD3FC" }}
                    aria-hidden="true"
                  >
                    {initials(activeProject)}
                  </span>
                  <div className="chat-sb-proj-meta">
                    <div className="chat-sb-proj-name">{activeProject.name}</div>
                    <div className={`chat-sb-proj-docs${docCounts[activeProject.project_id] === 0 ? " chat-sb-proj-docs-empty" : ""}`}>
                      {docCounts[activeProject.project_id] === 0 && <AlertCircle size={11} />}
                      {docLabel(activeProject)}
                    </div>
                  </div>
                  <ChevronDown size={14} style={{ transform: showProjMenu ? "rotate(180deg)" : "", transition: "transform var(--t-fast) var(--ease)" }} />
                </button>

                {showProjMenu && (
                  <div className="chat-sb-proj-menu fade-up" role="menu">
                    <div className="chat-sb-proj-menu-h">Select project</div>
                    {projectList.map((p) => (
                      <button
                        key={p.project_id}
                        role="menuitemradio"
                        aria-checked={p.project_id === activeProjectId}
                        className={`chat-sb-proj-item${p.project_id === activeProjectId ? " chat-sb-proj-item-active" : ""}`}
                        onClick={() => { setActiveProjectId(p.project_id); setShowProjMenu(false); }}
                      >
                        <span className="chat-sb-proj-init" style={{ background: (p.color ?? "#7DD3FC") + "30", color: p.color ?? "#7DD3FC" }} aria-hidden="true">
                          {initials(p)}
                        </span>
                        <div className="chat-sb-proj-meta">
                          <div className="chat-sb-proj-name">{p.name}</div>
                          <div className={`chat-sb-proj-docs${docCounts[p.project_id] === 0 ? " chat-sb-proj-docs-empty" : ""}`}>
                            {docLabel(p)}
                          </div>
                        </div>
                      </button>
                    ))}
                    {user?.role === "admin" && (
                      <div className="chat-sb-proj-foot">
                        <button className="chat-sb-proj-mng" role="menuitem" onClick={() => { setShowProjMenu(false); go("/admin"); }}>
                          <Settings size={13} />
                          {t("manageProjects")}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            <button className="chat-sb-new" onClick={() => { onMobileClose?.(); onNewChat(); }}>
              <Plus size={16} aria-hidden="true" />
              <span>{t("newChat")}</span>
              <kbd>⌘N</kbd>
            </button>

            <div className="chat-sb-search">
              <Search size={14} aria-hidden="true" />
              <input
                ref={searchRef}
                placeholder={t("searchPlaceholder")}
                aria-label={t("searchPlaceholder")}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <kbd>⌘K</kbd>
            </div>

            <nav className="chat-sb-history" aria-label={t("previous")}>
              {activeConvTitle && (
                <div className="chat-sb-group">
                  <div className="chat-sb-group-h">{t("currentConv")}</div>
                  <div className="chat-sb-item chat-sb-item-active" aria-current="page">
                    <span className="chat-sb-item-title">{activeConvTitle}</span>
                  </div>
                </div>
              )}
              {filteredConvs.length > 0 && (
                <div className="chat-sb-group">
                  <div className="chat-sb-group-h">{t("previous")}</div>
                  {filteredConvs.map((c) => {
                    const label = conversationLabel(c);
                    return (
                      <div key={c.id} className="chat-sb-item-wrap">
                        {renamingId === c.id ? (
                          <input
                            className="chat-sb-rename-input"
                            autoFocus
                            value={renameDraft}
                            onChange={(e) => setRenameDraft(e.target.value)}
                            onBlur={() => commitRename(c.id)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") commitRename(c.id);
                              if (e.key === "Escape") setRenamingId(null);
                            }}
                          />
                        ) : (
                          <>
                            <button className="chat-sb-item" onClick={() => go(`/chat/${c.id}`)}>
                              <span className="chat-sb-item-title">{label}</span>
                              <span className="chat-sb-item-time">
                                {new Date(c.updated_at.endsWith("Z") ? c.updated_at : c.updated_at + "Z")
                                  .toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                              </span>
                            </button>
                            <button
                              className="icon-btn chat-sb-item-more"
                              aria-label={t("conversationActions")}
                              aria-haspopup="menu"
                              aria-expanded={convMenuId === c.id}
                              onClick={(e) => { e.stopPropagation(); setConvMenuId(convMenuId === c.id ? null : c.id); }}
                            >
                              <MoreHorizontal size={13} />
                            </button>
                            {convMenuId === c.id && (
                              <div className="chat-sb-item-menu fade-up" role="menu" ref={convMenuRef}>
                                <button role="menuitem" onClick={() => startRename(c.id, label)}>
                                  <Pencil size={12} /> {t("renameConv")}
                                </button>
                                <button role="menuitem" className="chat-sb-item-menu-danger" onClick={() => handleDelete(c.id, label)}>
                                  <Trash2 size={12} /> {t("deleteConv")}
                                </button>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
              <button className="chat-sb-show-all" onClick={() => go("/history")}>
                {t("showAll")}
                {convPage && convPage.total > convList.length && ` (${convPage.total})`}
                <ChevronRight size={12} aria-hidden="true" />
              </button>
              <button className="chat-sb-show-all" onClick={() => go("/compare")}>
                <Columns2 size={12} aria-hidden="true" />
                {t("compare")}
              </button>
            </nav>

            <div className="chat-sb-foot" style={{ position: "relative" }} ref={userMenuRef}>
              {showUserMenu && (
                <div className="chat-sb-user-menu fade-up" role="menu">
                  <div style={{ padding: "12px 14px" }}>
                    <div style={{ fontSize: 12.5, fontWeight: 500, color: "var(--text)", wordBreak: "break-all" }}>
                      {displayName}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2, wordBreak: "break-all" }}>
                      {user?.email}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--text-muted)", marginTop: 3 }}>
                      <User size={11} aria-hidden="true" />
                      {user?.role === "admin" ? t("admin") : t("user")}
                    </div>
                  </div>
                  <div style={{ height: 1, background: "var(--border)" }} />
                  {onSettingsOpen && (
                    <button
                      className="chat-sb-user chat-sb-user-menu-item"
                      role="menuitem"
                      onClick={() => { setShowUserMenu(false); onSettingsOpen(); }}
                    >
                      <Settings size={13} /> {tTop("settings")}
                    </button>
                  )}
                  <button className="chat-sb-user chat-sb-user-menu-item" role="menuitem" onClick={handleLogout}>
                    <LogOut size={13} />
                    {t("logout")}
                  </button>
                </div>
              )}
              <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
                <button
                  className="chat-sb-user"
                  style={{ flex: 1 }}
                  onClick={() => setShowUserMenu((v) => !v)}
                  aria-haspopup="menu"
                  aria-expanded={showUserMenu}
                >
                  <div className="chat-sb-avatar" aria-hidden="true">{avatarText}</div>
                  <div className="chat-sb-user-meta">
                    <div className="chat-sb-user-name">{displayName}</div>
                    <div className="chat-sb-user-plan">
                      {user?.role === "admin" ? t("admin") : t("user")}
                    </div>
                  </div>
                </button>
                {user?.role === "admin" && (
                  <button
                    className="icon-btn chat-sb-user-cog"
                    style={{ padding: "6px 10px", flexShrink: 0 }}
                    title="Admin panel"
                    aria-label="Admin panel"
                    onClick={() => go("/admin")}
                  >
                    <Settings size={14} />
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </aside>
    </>
  );
}

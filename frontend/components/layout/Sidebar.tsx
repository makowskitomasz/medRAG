"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Activity, ChevronRight, ChevronDown, Plus, Search, Settings, LogOut, User,
} from "lucide-react";
import { useUIStore } from "@/store";
import { useProjects } from "@/hooks/useProjects";
import { useConversations } from "@/hooks/useConversations";
import { auth, Project } from "@/lib/api";
import { clearAuth, getUser, saveUser } from "@/lib/auth";

interface Props {
  onNewChat: () => void;
  activeConvTitle?: string;
}

export default function Sidebar({ onNewChat, activeConvTitle }: Props) {
  const router = useRouter();
  const t = useTranslations("sidebar");
  const { sidebarCollapsed, setSidebarCollapsed, activeProjectId, setActiveProjectId } = useUIStore();
  const [showProjMenu, setShowProjMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [search, setSearch] = useState("");
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    };
    if (showUserMenu) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showUserMenu]);
  const { data: projectList = [] } = useProjects();
  const { data: convList = [] } = useConversations(activeProjectId);

  useEffect(() => {
    if (!activeProjectId && projectList.length > 0) {
      setActiveProjectId(projectList[0].project_id);
    }
  }, [activeProjectId, projectList, setActiveProjectId]);

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
    !search || (c.first_user_message ?? "").toLowerCase().includes(search.toLowerCase())
  );

  const initials = (p: Project) => p.initials ?? p.name.slice(0, 2).toUpperCase();

  const handleLogout = () => {
    clearAuth();
    router.replace("/login");
  };

  return (
    <aside className={`chat-sidebar${sidebarCollapsed ? " chat-sidebar-collapsed" : ""}`}>
      <div className="chat-sb-head">
        <button className="chat-sb-logo" onClick={() => router.push("/chat/new")}>
          <Activity size={22} />
          {!sidebarCollapsed && <span>medRAG</span>}
        </button>
        <button
          className="icon-btn chat-sb-collapse"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          title={sidebarCollapsed ? "Expand" : "Collapse"}
        >
          <ChevronRight size={14} style={{ transform: sidebarCollapsed ? "" : "rotate(180deg)" }} />
        </button>
      </div>

      {!sidebarCollapsed && (
        <>
          {!activeProject && user?.role === "admin" && (
            <div style={{ padding: "10px 12px" }}>
              <button
                className="chat-sb-proj-mng"
                style={{ width: "100%", justifyContent: "center", padding: "8px 12px" }}
                onClick={() => router.push("/admin")}
              >
                <Settings size={13} />
                {t("manageProjects")}
              </button>
            </div>
          )}

          {activeProject && (
            <div className="chat-sb-project">
              <button className="chat-sb-proj-btn" onClick={() => setShowProjMenu(!showProjMenu)}>
                <span
                  className="chat-sb-proj-init"
                  style={{ background: (activeProject.color ?? "#7DD3FC") + "30", color: activeProject.color ?? "#7DD3FC" }}
                >
                  {initials(activeProject)}
                </span>
                <div className="chat-sb-proj-meta">
                  <div className="chat-sb-proj-name">{activeProject.name}</div>
                  <div className="chat-sb-proj-docs">{activeProject.description || "—"}</div>
                </div>
                <ChevronDown size={14} style={{ transform: showProjMenu ? "rotate(180deg)" : "", transition: "transform var(--t-fast) var(--ease)" }} />
              </button>

              {showProjMenu && (
                <div className="chat-sb-proj-menu fade-up">
                  <div className="chat-sb-proj-menu-h">Select project</div>
                  {projectList.map((p) => (
                    <button
                      key={p.project_id}
                      className={`chat-sb-proj-item${p.project_id === activeProjectId ? " chat-sb-proj-item-active" : ""}`}
                      onClick={() => { setActiveProjectId(p.project_id); setShowProjMenu(false); }}
                    >
                      <span className="chat-sb-proj-init" style={{ background: (p.color ?? "#7DD3FC") + "30", color: p.color ?? "#7DD3FC" }}>
                        {initials(p)}
                      </span>
                      <div className="chat-sb-proj-meta">
                        <div className="chat-sb-proj-name">{p.name}</div>
                        <div className="chat-sb-proj-docs">{p.description}</div>
                      </div>
                    </button>
                  ))}
                  <div className="chat-sb-proj-foot">
                    <button className="chat-sb-proj-mng" onClick={() => { setShowProjMenu(false); router.push("/admin"); }}>
                      <Settings size={13} />
                      {t("manageProjects")}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          <button className="chat-sb-new" onClick={onNewChat}>
            <Plus size={16} />
            <span>{t("newChat")}</span>
            <kbd>⌘N</kbd>
          </button>

          <div className="chat-sb-search">
            <Search size={14} />
            <input
              placeholder={t("searchPlaceholder")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <kbd>⌘K</kbd>
          </div>

          <nav className="chat-sb-history">
            {activeConvTitle && (
              <div className="chat-sb-group">
                <div className="chat-sb-group-h">{t("currentConv")}</div>
                <button className="chat-sb-item chat-sb-item-active">
                  <span className="chat-sb-item-title">{activeConvTitle}</span>
                </button>
              </div>
            )}
            {filteredConvs.length > 0 && (
              <div className="chat-sb-group">
                <div className="chat-sb-group-h">{t("previous")}</div>
                {filteredConvs.slice(0, 10).map((c) => (
                  <button
                    key={c.id}
                    className="chat-sb-item"
                    onClick={() => router.push(`/chat/${c.id}`)}
                  >
                    <span className="chat-sb-item-title">
                      {c.first_user_message ?? `Conv ${c.id.slice(-6)}`}
                    </span>
                    <span className="chat-sb-item-time">
                      {new Date(c.updated_at.endsWith("Z") ? c.updated_at : c.updated_at + "Z")
                        .toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </button>
                ))}
              </div>
            )}
            <button className="chat-sb-show-all" onClick={() => router.push("/history")}>
              {t("showAll")}
              <ChevronRight size={12} />
            </button>
          </nav>

          <div className="chat-sb-foot" style={{ position: "relative" }} ref={userMenuRef}>
            {showUserMenu && (
              <div
                className="fade-up"
                style={{
                  position: "absolute", bottom: "calc(100% + 6px)", left: 10, right: 10,
                  background: "var(--bg-elev)", border: "1px solid var(--border-strong)",
                  borderRadius: "var(--r-md)", boxShadow: "var(--shadow-lg)", zIndex: 50,
                  overflow: "hidden",
                }}
              >
                <div style={{ padding: "12px 14px" }}>
                  <div style={{ fontSize: 12.5, fontWeight: 500, color: "var(--text)", wordBreak: "break-all" }}>
                    {displayName}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2, wordBreak: "break-all" }}>
                    {user?.email}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--text-muted)", marginTop: 3 }}>
                    <User size={11} />
                    {user?.role === "admin" ? t("admin") : t("user")}
                  </div>
                </div>
                <div style={{ height: 1, background: "var(--border)" }} />
                <button
                  style={{
                    display: "flex", alignItems: "center", gap: 8, width: "100%",
                    padding: "10px 14px", fontSize: 13, color: "var(--text-2)",
                  }}
                  className="chat-sb-user"
                  onClick={handleLogout}
                >
                  <LogOut size={13} />
                  {t("logout")}
                </button>
              </div>
            )}
            <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
              <button className="chat-sb-user" style={{ flex: 1 }} onClick={() => setShowUserMenu((v) => !v)}>
                <div className="chat-sb-avatar">
                  {avatarText}
                </div>
                <div className="chat-sb-user-meta">
                  <div className="chat-sb-user-name">{displayName}</div>
                  <div className="chat-sb-user-plan">
                    {user?.role === "admin" ? t("admin") : t("user")}
                  </div>
                </div>
              </button>
              <button
                className="icon-btn chat-sb-user-cog"
                style={{ padding: "6px 10px", flexShrink: 0 }}
                title="Admin panel"
                onClick={() => router.push("/admin")}
              >
                <Settings size={14} />
              </button>
            </div>
          </div>
        </>
      )}
    </aside>
  );
}

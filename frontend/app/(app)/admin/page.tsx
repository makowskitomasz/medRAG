"use client";
export const dynamic = "force-dynamic";
import { useState, useRef, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronRight, Plus, Upload, Search, FileText,
  Layers, Brain, MessageSquare, Trash2, User, Settings, Check, X as XIcon,
} from "lucide-react";
import { projects, documents, Project, Document, CreateProjectInput } from "@/lib/api";
import { useUIStore } from "@/store";
import { useSettingsOptions, useUpdateSettings, useUpdateProject } from "@/hooks/useProjects";

const RAG_MODE_LABEL: Record<string, string> = {
  vanilla: "Vanilla",
  hyde: "HyDE",
  query_rewriting: "Query Rewriting",
  self_reflection: "Self-Reflection",
  multi_agent: "Multi-Agent",
  corrective_rag: "Corrective RAG",
  iterative_multihop: "Iterative MultiHop",
  madam_rag: "MADAM RAG",
  rare_rag: "RARE RAG (auto-routing)",
};

const RAG_MODES = Object.entries(RAG_MODE_LABEL).map(([id, label]) => ({ id, label }));

function StatusBadge({ status }: { status: string }) {
  const t = useTranslations("admin");
  const key = `status_${status}` as Parameters<typeof t>[0];
  return (
    <span className={`adm-status adm-status-${status}`}>
      <span className="adm-status-dot" />
      <span>{t(key)}</span>
    </span>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + " kB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

const fieldStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 5,
};
const labelStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  textTransform: "uppercase" as const,
  letterSpacing: "0.05em",
  color: "var(--text-muted)",
};
const inputStyle: React.CSSProperties = {
  padding: "8px 10px",
  borderRadius: "var(--r-md)",
  border: "1px solid var(--border-strong)",
  background: "var(--bg-elev)",
  color: "var(--text)",
  fontSize: 13,
  width: "100%",
  outline: "none",
};
const hintStyle: React.CSSProperties = {
  fontSize: 11,
  color: "var(--text-muted)",
  marginTop: 1,
};

function SettingsModal({ project, onClose }: { project: Project; onClose: () => void }) {
  const t = useTranslations("admin");
  const [saved, setSaved] = useState(false);

  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description);
  const [ragMode, setRagMode] = useState(project.settings.rag_mode);
  const [chunkingStrategy, setChunkingStrategy] = useState(project.settings.chunking_strategy);
  const [embeddingProvider, setEmbeddingProvider] = useState(project.settings.embedding_provider);
  const [hybridAlpha, setHybridAlpha] = useState(project.settings.hybrid_alpha);
  const [topK, setTopK] = useState(project.settings.top_k);
  const [rerankTopN, setRerankTopN] = useState(project.settings.rerank_top_n);

  const { data: options } = useSettingsOptions();
  const updateSettings = useUpdateSettings(project.id);
  const updateProject = useUpdateProject(project.id);

  const isPending = updateSettings.isPending || updateProject.isPending;
  const isError = updateSettings.isError || updateProject.isError;

  const ragOptions = options?.rag_modes ?? [{ value: ragMode, label: ragMode, description: "" }];
  const chunkingOptions = options?.chunking_strategies ?? [{ value: chunkingStrategy, label: chunkingStrategy, description: "" }];
  const embeddingOptions = options?.embedding_providers ?? [{ value: embeddingProvider, label: embeddingProvider, description: "" }];
  const alphaConstraint = options?.hybrid_alpha;
  const topKConstraint = options?.top_k;
  const rerankConstraint = options?.rerank_top_n;

  const handleSave = async () => {
    await Promise.all([
      updateProject.mutateAsync({ name, description }),
      updateSettings.mutateAsync({
        rag_mode: ragMode,
        chunking_strategy: chunkingStrategy,
        embedding_provider: embeddingProvider,
        hybrid_alpha: hybridAlpha,
        top_k: topK,
        rerank_top_n: rerankTopN,
      }),
    ]);
    setSaved(true);
    setTimeout(() => { setSaved(false); onClose(); }, 1200);
  };

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 200,
        background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 24,
      }}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        background: "var(--bg-elev)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-xl, 16px)",
        width: "100%", maxWidth: 700,
        maxHeight: "90vh", overflowY: "auto",
        boxShadow: "0 24px 64px rgba(0,0,0,0.4)",
        display: "flex", flexDirection: "column",
      }}>
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "20px 24px 16px",
          borderBottom: "1px solid var(--border)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Settings size={16} style={{ color: "var(--text-muted)" }} />
            <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text)" }}>{t("settings")}</span>
            <span style={{
              fontSize: 11, fontWeight: 600, color: "var(--text-muted)",
              background: "var(--bg-subtle)", border: "1px solid var(--border)",
              borderRadius: 6, padding: "2px 7px",
            }}>{project.name}</span>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 4, borderRadius: 6, lineHeight: 1 }}
          >
            <XIcon size={16} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20 }}>

          {/* Name + description */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div style={{ ...fieldStyle, gridColumn: "1 / -1" }}>
              <label style={labelStyle}>{t("field_name")}</label>
              <input style={inputStyle} type="text" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div style={{ ...fieldStyle, gridColumn: "1 / -1" }}>
              <label style={labelStyle}>{t("field_description")}</label>
              <input style={inputStyle} type="text" value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
          </div>

          {/* Divider */}
          <div style={{ borderTop: "1px solid var(--border)", marginTop: -4 }} />

          {/* Strategy dropdowns */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            <div style={fieldStyle}>
              <label style={labelStyle}>{t("field_rag_mode")}</label>
              <select style={inputStyle} value={ragMode} onChange={(e) => setRagMode(e.target.value)}>
                {ragOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>{t("field_chunking_strategy")}</label>
              <select style={inputStyle} value={chunkingStrategy} onChange={(e) => setChunkingStrategy(e.target.value)}>
                {chunkingOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>{t("field_embedding_provider")}</label>
              <select style={inputStyle} value={embeddingProvider} onChange={(e) => setEmbeddingProvider(e.target.value)}>
                {embeddingOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>

          {/* Numeric params */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            <div style={fieldStyle}>
              <label style={labelStyle}>{t("field_hybrid_alpha")}</label>
              <input style={inputStyle} type="number" value={hybridAlpha}
                step={alphaConstraint?.step ?? 0.05} min={alphaConstraint?.min ?? 0} max={alphaConstraint?.max ?? 1}
                onChange={(e) => setHybridAlpha(parseFloat(e.target.value))} />
              <span style={hintStyle}>{t("hint_hybrid_alpha")}</span>
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>{t("field_top_k")}</label>
              <input style={inputStyle} type="number" value={topK}
                step={topKConstraint?.step ?? 1} min={topKConstraint?.min ?? 1} max={topKConstraint?.max ?? 100}
                onChange={(e) => setTopK(parseInt(e.target.value))} />
              <span style={hintStyle}>{t("hint_top_k")}</span>
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>{t("field_rerank_top_n")}</label>
              <input style={inputStyle} type="number" value={rerankTopN}
                step={rerankConstraint?.step ?? 1} min={rerankConstraint?.min ?? 1} max={rerankConstraint?.max ?? 20}
                onChange={(e) => setRerankTopN(parseInt(e.target.value))} />
              <span style={hintStyle}>{t("hint_rerank_top_n")}</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 24px 20px",
          borderTop: "1px solid var(--border)",
        }}>
          <div style={{ fontSize: 12, height: 20 }}>
            {saved && <span style={{ color: "var(--c-accent-mint)", display: "flex", alignItems: "center", gap: 5 }}><Check size={13} />{t("settingsSaved")}</span>}
            {isError && <span style={{ color: "#EF4444" }}>{t("settingsError")}</span>}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn" onClick={onClose} disabled={isPending}>{t("cancel")}</button>
            <button className="btn btn-primary" onClick={handleSave} disabled={isPending}>
              {isPending ? t("savingSettings") : t("saveSettings")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { setActiveProjectId } = useUIStore();

  const t = useTranslations("admin");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [dragHover, setDragHover] = useState(false);
  const [docSearch, setDocSearch] = useState("");
  const [showNewForm, setShowNewForm] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newRagMode, setNewRagMode] = useState("vanilla");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: projectList = [], isLoading: projLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: projects.list,
    staleTime: 30_000,
  });

  const active = activeId ? projectList.find((p) => p.project_id === activeId) : projectList[0];

  const { data: docList = [], isLoading: docLoading } = useQuery({
    queryKey: ["documents", active?.project_id],
    queryFn: () => documents.list(active!.project_id),
    enabled: !!active,
    refetchInterval: (query) => {
      const docs = query.state.data as Document[] | undefined;
      if (!docs) return false;
      const processing = docs.some((d) => d.status !== "indexed" && d.status !== "failed");
      return processing ? 3000 : false;
    },
  });


  const createProject = useMutation({
    mutationFn: (data: CreateProjectInput) => projects.create(data),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setActiveId(p.project_id);
      setActiveProjectId(p.project_id);
      setShowNewForm(false);
      setNewName("");
      setNewDesc("");
      setNewRagMode("vanilla");
    },
  });

  const deleteProject = useMutation({
    mutationFn: (id: string) => projects.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });

  const uploadDoc = useMutation({
    mutationFn: (file: File) => documents.upload(active!.project_id, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents", active?.project_id] }),
  });

  const deleteDoc = useMutation({
    mutationFn: ({ projectId, docId }: { projectId: string; docId: string }) =>
      documents.delete(projectId, docId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents", active?.project_id] }),
  });

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragHover(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadDoc.mutate(file);
  }, [uploadDoc]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadDoc.mutate(file);
    e.target.value = "";
  };

  const filteredDocs = docList.filter((d) =>
    !docSearch || d.filename.toLowerCase().includes(docSearch.toLowerCase())
  );

  const indexedCount = docList.filter((d) => d.status === "indexed").length;
  const failedCount = docList.filter((d) => d.status === "failed").length;
  const totalChunks = docList.reduce((s, d) => s + (d.chunk_count ?? 0), 0);

  return (
    <div className="adm-root fade-in">
      {/* Left rail */}
      <aside className="adm-rail">
        <div className="adm-rail-head">
          <button className="btn-ghost adm-back" onClick={() => router.back()}>
            <ChevronRight size={14} style={{ transform: "rotate(180deg)" }} />
            <span>{t("backToChats")}</span>
          </button>
          <h2>{t("projects")}</h2>
        </div>

        <button className="adm-new-project" onClick={() => setShowNewForm(!showNewForm)}>
          <Plus size={14} />
          <span>{t("newProject")}</span>
        </button>

        {showNewForm && (
          <form
            style={{ margin: "0 12px 12px", display: "flex", flexDirection: "column", gap: 8 }}
            onSubmit={(e) => {
              e.preventDefault();
              if (newName.trim()) createProject.mutate({ name: newName, description: newDesc, rag_mode: newRagMode });
            }}
          >
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={t("projectNamePlaceholder")}
              style={{
                padding: "8px 10px", borderRadius: "var(--r-md)", border: "1px solid var(--border-strong)",
                background: "var(--bg-elev)", color: "var(--text)", fontSize: 13,
              }}
            />
            <input
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              placeholder={t("descriptionPlaceholder")}
              style={{
                padding: "8px 10px", borderRadius: "var(--r-md)", border: "1px solid var(--border)",
                background: "var(--bg-elev)", color: "var(--text)", fontSize: 12,
              }}
            />
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <label style={{ fontSize: 11, color: "var(--text-muted)", paddingLeft: 2 }}>{t("ragModeLabel")}</label>
              <select
                value={newRagMode}
                onChange={(e) => setNewRagMode(e.target.value)}
                style={{
                  padding: "7px 10px", borderRadius: "var(--r-md)", border: "1px solid var(--border)",
                  background: "var(--bg-elev)", color: "var(--text)", fontSize: 12, cursor: "pointer",
                }}
              >
                {RAG_MODES.map(({ id, label }) => (
                  <option key={id} value={id}>{label}</option>
                ))}
              </select>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <button
                type="submit"
                className="btn btn-primary"
                style={{ flex: 1, padding: "7px 10px", fontSize: 12 }}
                disabled={createProject.isPending}
              >
                {createProject.isPending ? t("creating") : t("create")}
              </button>
              <button type="button" className="btn" style={{ padding: "7px 10px", fontSize: 12 }} onClick={() => setShowNewForm(false)}>
                {t("cancel")}
              </button>
            </div>
          </form>
        )}

        <div className="adm-rail-list stagger">
          {projLoading && <div style={{ padding: "12px 8px", fontSize: 12, color: "var(--text-muted)" }}>{t("loading")}</div>}
          {projectList.map((p) => (
            <button
              key={p.project_id}
              className={`adm-rail-item${(active?.project_id === p.project_id) ? " adm-rail-item-active" : ""}`}
              onClick={() => { setActiveId(p.project_id); setActiveProjectId(p.project_id); }}
            >
              <span className="adm-rail-bar" style={{ background: p.color ?? "#7DD3FC" }} />
              <span
                className="chat-sb-proj-init"
                style={{ background: (p.color ?? "#7DD3FC") + "30", color: p.color ?? "#7DD3FC" }}
              >
                {p.initials ?? p.name.slice(0, 2).toUpperCase()}
              </span>
              <div className="adm-rail-meta">
                <div className="adm-rail-name">{p.name}</div>
                <div className="adm-rail-sub">{docList.length} {t("docCount")}</div>
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* Main */}
      <main className="adm-main">
        {!active ? (
          <div className="chat-empty" style={{ marginTop: 60 }}>
            <div className="chat-empty-icon"><Layers size={48} /></div>
            <h3>{t("noProjects")}</h3>
            <p>{t("noProjectsHint")}</p>
          </div>
        ) : (
          <>
            <div className="adm-detail-head">
              <div className="adm-detail-head-l">
                <div className="adm-bc">
                  <span>Admin</span>
                  <ChevronRight size={12} />
                  <span>{t("projects")}</span>
                  <ChevronRight size={12} />
                  <strong>{active.name}</strong>
                </div>
                <div className="adm-detail-title">
                  <div
                    className="adm-detail-init"
                    style={{ background: (active.color ?? "#7DD3FC") + "20", color: active.color ?? "#7DD3FC" }}
                  >
                    {active.initials ?? active.name.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h1>{active.name}</h1>
                    <p>{active.description || t("noDescription")}</p>
                  </div>
                </div>
              </div>
              <div className="adm-detail-actions">
                <button
                  className="btn"
                  onClick={() => { setActiveProjectId(active.project_id); router.push("/chat/new"); }}
                >
                  <MessageSquare size={14} /> {t("conversations")}
                </button>
                <button className="btn" onClick={() => setShowSettings(true)}>
                  <Settings size={14} /> {t("editSettings")}
                </button>
                <button
                  className="btn"
                  style={{ color: "#EF4444" }}
                  onClick={() => {
                    if (confirm(t("deleteProjectConfirm", { name: active.name }))) {
                      deleteProject.mutate(active.project_id);
                      setActiveId(null);
                    }
                  }}
                >
                  <Trash2 size={14} /> {t("delete")}
                </button>
                <button className="btn btn-primary" onClick={() => fileInputRef.current?.click()}>
                  <Upload size={14} /> {t("uploadPDF")}
                </button>
                <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,.md" style={{ display: "none" }} onChange={handleFileInput} />
              </div>
            </div>

            {/* Stats */}
            <div className="adm-stats stagger">
              <div className="adm-stat">
                <div className="adm-stat-l"><FileText size={16} /><span>{t("stats_docs")}</span></div>
                <div className="adm-stat-v">{docList.length}</div>
                <div className="adm-stat-s">{indexedCount} indexed{failedCount > 0 ? ` · ${failedCount} failed` : ""}</div>
              </div>
              <div className="adm-stat">
                <div className="adm-stat-l"><Layers size={16} /><span>{t("stats_chunks")}</span></div>
                <div className="adm-stat-v">{totalChunks || "—"}</div>
                <div className="adm-stat-s">{t("stats_after_indexing")}</div>
              </div>
              <div className="adm-stat">
                <div className="adm-stat-l"><Brain size={16} /><span>{t("stats_embedding")}</span></div>
                <div className="adm-stat-v" style={{ fontSize: 14 }}>{active.settings.embedding_provider}</div>
                <div className="adm-stat-s">Mode: {RAG_MODE_LABEL[active.settings.rag_mode] ?? active.settings.rag_mode}</div>
              </div>
              <div className="adm-stat">
                <div className="adm-stat-l"><User size={16} /><span>Chunking</span></div>
                <div className="adm-stat-v" style={{ fontSize: 14 }}>{active.settings.chunking_strategy}</div>
                <div className="adm-stat-s">top_k: {active.settings.top_k}</div>
              </div>
            </div>

            {/* Settings modal */}
            {showSettings && <SettingsModal project={active} onClose={() => setShowSettings(false)} />}

            {/* Drop zone */}
            <div
              className={`adm-drop${dragHover ? " adm-drop-hover" : ""}`}
              onDragEnter={(e) => { e.preventDefault(); setDragHover(true); }}
              onDragLeave={() => setDragHover(false)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="adm-drop-ic"><Upload size={20} /></div>
              <div>
                <strong>{t("dropTitle")}</strong>
                <span> or <a href="#" onClick={(e) => e.preventDefault()}>{t("dropSelect")}</a>. {t("dropMax")}</span>
              </div>
              <div className="adm-drop-formats">
                <span>PDF</span><span>DOCX</span><span>MD</span><span>TXT</span>
              </div>
            </div>

            {/* Upload status */}
            {uploadDoc.isPending && (
              <div style={{ margin: "-8px 32px 12px", padding: "8px 12px", background: "var(--accent-soft)", borderRadius: "var(--r-md)", fontSize: 13, color: "var(--text-2)", display: "flex", alignItems: "center", gap: 8 }}>
                <div className="search-spinner search-spinner-sm" /> {t("uploading")}
              </div>
            )}
            {uploadDoc.isError && (
              <div style={{ margin: "-8px 32px 12px", padding: "8px 12px", background: "rgba(239,68,68,0.1)", borderRadius: "var(--r-md)", fontSize: 13, color: "#EF4444" }}>
                Error: {uploadDoc.error?.message}
              </div>
            )}

            {/* Documents table */}
            <div className="adm-docs">
              <div className="adm-docs-head">
                <h3>{t("documents")}</h3>
                <div className="adm-docs-tools">
                  <div className="hist-search adm-docs-search">
                    <Search size={13} />
                    <input placeholder={t("filterPlaceholder")} value={docSearch} onChange={(e) => setDocSearch(e.target.value)} />
                  </div>
                </div>
              </div>
              <div className="adm-table">
                <div className="adm-row adm-row-head">
                  <span className="adm-col-name">Name</span>
                  <span className="adm-col-size">Size</span>
                  <span className="adm-col-pages">Pages</span>
                  <span className="adm-col-chunks">Chunks</span>
                  <span className="adm-col-status">Status</span>
                  <span className="adm-col-date">Added</span>
                  <span className="adm-col-act" />
                </div>
                {docLoading && (
                  <div className="adm-row adm-row-data" style={{ gridTemplateColumns: "1fr", justifyContent: "center" }}>
                    <span style={{ fontSize: 12, color: "var(--text-muted)", padding: "16px 0" }}>{t("loadingDocs")}</span>
                  </div>
                )}
                {!docLoading && filteredDocs.length === 0 && (
                  <div className="adm-row adm-row-data" style={{ gridTemplateColumns: "1fr" }}>
                    <span style={{ fontSize: 12, color: "var(--text-muted)", padding: "16px 0" }}>{t("noDocs")}</span>
                  </div>
                )}
                {filteredDocs.map((d) => (
                  <div key={d.document_id} className={`adm-row adm-row-data${d.status === "failed" ? " adm-row-failed" : ""}`}>
                    <div className="adm-col-name">
                      <FileText size={16} className="adm-col-icon" />
                      <div className="adm-col-name-meta">
                        <div className="adm-col-name-t" title={d.filename}>{d.filename}</div>
                      </div>
                    </div>
                    <span className="adm-col-size">{d.file_size != null ? formatBytes(d.file_size) : "—"}</span>
                    <span className="adm-col-pages">{d.page_count ?? "—"}</span>
                    <span className="adm-col-chunks">{d.chunk_count ?? "—"}</span>
                    <span className="adm-col-status"><StatusBadge status={d.status} /></span>
                    <span className="adm-col-date">
                      {(() => {
                        const raw = d.created_at ?? d.status_history?.[0]?.timestamp ?? d.status_history?.[0]?.ts;
                        if (!raw) return "—";
                        const iso = raw.endsWith("Z") ? raw : raw + "Z";
                        return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
                      })()}
                    </span>
                    <span className="adm-col-act">
                      <button
                        className="icon-btn"
                        title="Delete"
                        onClick={() => {
                          if (confirm(t("deleteDocConfirm", { name: d.filename })))
                            deleteDoc.mutate({ projectId: active.project_id, docId: d.document_id });
                        }}
                      >
                        <Trash2 size={14} style={{ color: "#EF4444" }} />
                      </button>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

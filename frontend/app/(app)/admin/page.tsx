"use client";
export const dynamic = "force-dynamic";
import { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronRight, Plus, Upload, Search, FileText,
  Layers, Brain, MessageSquare, Trash2, User, Settings, Check, X as XIcon, Users,
  ChevronDown, ChevronUp, RotateCcw,
} from "lucide-react";
import { projects, documents, auth, Project, DocumentsPage, CreateProjectInput, User as UserType, PromptSlot } from "@/lib/api";
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

function PromptSlotRow({
  slot,
  override,
  onSave,
  onReset,
}: {
  slot: PromptSlot;
  override: string | undefined;
  onSave: (slug: string, value: string) => void;
  onReset: (slug: string) => void;
}) {
  const isOverridden = override !== undefined;
  const [expanded, setExpanded] = useState(false);
  const [draft, setDraft] = useState(override ?? slot.default_template);

  const handleExpand = () => {
    if (!expanded) setDraft(override ?? slot.default_template);
    setExpanded((v) => !v);
  };

  const handleSave = () => {
    onSave(slot.slug, draft);
    setExpanded(false);
  };

  const handleReset = () => {
    onReset(slot.slug);
    setDraft(slot.default_template);
    setExpanded(false);
  };

  return (
    <div style={{
      borderRadius: "var(--r-md)",
      border: "1px solid var(--border)",
      overflow: "hidden",
    }}>
      <button
        onClick={handleExpand}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: 10,
          padding: "10px 14px", background: "none", border: "none",
          cursor: "pointer", textAlign: "left",
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{slot.label}</span>
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{slot.description}</div>
        </div>
        {expanded ? <ChevronUp size={14} style={{ color: "var(--text-muted)", flexShrink: 0 }} /> : <ChevronDown size={14} style={{ color: "var(--text-muted)", flexShrink: 0 }} />}
      </button>

      {expanded && (
        <div style={{ padding: "0 14px 14px", display: "flex", flexDirection: "column", gap: 8 }}>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={10}
            style={{
              ...inputStyle,
              fontFamily: "monospace",
              fontSize: 12,
              resize: "vertical",
              lineHeight: 1.5,
              opacity: isOverridden ? 1 : 0.55,
            }}
          />
          {!isOverridden && (
            <p style={{ fontSize: 11, color: "var(--text-muted)", margin: 0 }}>
              Currently using default template. Edit above and save to override.
            </p>
          )}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            {isOverridden && (
              <button
                className="btn"
                onClick={handleReset}
                style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12 }}
                title="Revert to default"
              >
                <RotateCcw size={12} /> Reset to default
              </button>
            )}
            <button
              className="btn btn-primary"
              onClick={handleSave}
              style={{ fontSize: 12 }}
            >
              Save override
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function SettingsModal({ project, onClose }: { project: Project; onClose: () => void }) {
  const t = useTranslations("admin");
  const qc = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<"settings" | "members" | "prompts">("settings");

  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description);
  const [llmModel, setLlmModel] = useState(project.settings.llm_model ?? "openai/gpt-oss-120b");
  const [chunkingStrategy, setChunkingStrategy] = useState(project.settings.chunking_strategy);
  const [embeddingProvider, setEmbeddingProvider] = useState(project.settings.embedding_provider);
  const [hybridAlpha, setHybridAlpha] = useState(project.settings.hybrid_alpha);
  const [topK, setTopK] = useState(project.settings.top_k);
  const [rerankTopN, setRerankTopN] = useState(project.settings.rerank_top_n);
  // Edited as one question per line — a list is friendlier than JSON here.
  const [sampleQuestions, setSampleQuestions] = useState(
    (project.settings.sample_questions ?? []).join("\n")
  );

  const { data: options } = useSettingsOptions();
  const updateSettings = useUpdateSettings(project.id);
  const updateProject = useUpdateProject(project.id);

  const deletePromptOverride = useMutation({
    mutationFn: (slug: string) => projects.deletePromptOverride(project.id, slug),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });

  const { data: allUsers = [] } = useQuery<UserType[]>({
    queryKey: ["users"],
    queryFn: auth.listUsers,
    staleTime: 60_000,
  });

  const addMember = useMutation({
    mutationFn: (userId: string) => projects.addMember(project.id, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });

  const removeMember = useMutation({
    mutationFn: (userId: string) => projects.removeMember(project.id, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });

  const memberIds = project.member_ids ?? [];
  const members = allUsers.filter((u) => memberIds.includes(u.id));
  const nonMembers = allUsers.filter((u) => !memberIds.includes(u.id));

  const isPending = updateSettings.isPending || updateProject.isPending;
  const isError = updateSettings.isError || updateProject.isError;

  const llmOptions = options?.llm_models ?? [{ value: llmModel, label: llmModel, description: "" }];
  const chunkingOptions = options?.chunking_strategies ?? [{ value: chunkingStrategy, label: chunkingStrategy, description: "" }];
  const embeddingOptions = options?.embedding_providers ?? [{ value: embeddingProvider, label: embeddingProvider, description: "" }];
  const alphaConstraint = options?.hybrid_alpha;
  const topKConstraint = options?.top_k;
  const rerankConstraint = options?.rerank_top_n;
  const promptSlots = options?.prompt_slots ?? [];
  const promptOverrides: Record<string, string> = project.settings.prompt_overrides ?? {};

  const handleSave = async () => {
    await Promise.all([
      updateProject.mutateAsync({ name, description }),
      updateSettings.mutateAsync({
        llm_model: llmModel,
        chunking_strategy: chunkingStrategy,
        embedding_provider: embeddingProvider,
        hybrid_alpha: hybridAlpha,
        top_k: topK,
        rerank_top_n: rerankTopN,
        sample_questions: sampleQuestions
          .split("\n")
          .map((q) => q.trim())
          .filter(Boolean)
          .slice(0, 6),
      }),
    ]);
    setSaved(true);
    setTimeout(() => { setSaved(false); onClose(); }, 1200);
  };

  const handlePromptSave = async (slug: string, value: string) => {
    await updateSettings.mutateAsync({ prompt_overrides: { [slug]: value } });
    qc.invalidateQueries({ queryKey: ["projects"] });
  };

  const handlePromptReset = (slug: string) => {
    deletePromptOverride.mutate(slug);
  };

  const tabBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: "6px 14px",
    fontSize: 13,
    fontWeight: 600,
    borderRadius: "var(--r-md)",
    border: "none",
    cursor: "pointer",
    background: active ? "var(--bg-subtle)" : "none",
    color: active ? "var(--text)" : "var(--text-muted)",
  });

  const userDisplayName = (u: UserType) => {
    const full = [u.first_name, u.last_name].filter(Boolean).join(" ");
    return full ? `${full} (${u.email})` : u.email;
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

        {/* Tabs */}
        <div style={{
          display: "flex", gap: 4, padding: "10px 24px 0",
          borderBottom: "1px solid var(--border)",
        }}>
          <button style={tabBtnStyle(activeTab === "settings")} onClick={() => setActiveTab("settings")}>
            <Settings size={13} style={{ display: "inline", marginRight: 5, verticalAlign: "middle" }} />
            Settings
          </button>
          <button style={tabBtnStyle(activeTab === "members")} onClick={() => setActiveTab("members")}>
            <Users size={13} style={{ display: "inline", marginRight: 5, verticalAlign: "middle" }} />
            Members
          </button>
          <button style={tabBtnStyle(activeTab === "prompts")} onClick={() => setActiveTab("prompts")}>
            <Brain size={13} style={{ display: "inline", marginRight: 5, verticalAlign: "middle" }} />
            Prompts
          </button>
        </div>

        {/* Body — Settings */}
        {activeTab === "settings" && (
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
                <label style={labelStyle}>LLM Model</label>
                <select style={inputStyle} value={llmModel} onChange={(e) => setLlmModel(e.target.value)}>
                  {llmOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
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

              <div style={{ ...fieldStyle, gridColumn: "1 / -1" }}>
                <label style={labelStyle}>{t("field_sample_questions")}</label>
                <textarea
                  style={{ ...inputStyle, resize: "vertical", lineHeight: 1.5 }}
                  rows={4}
                  value={sampleQuestions}
                  onChange={(e) => setSampleQuestions(e.target.value)}
                  placeholder={t("placeholder_sample_questions")}
                />
                <span style={hintStyle}>{t("hint_sample_questions")}</span>
              </div>
            </div>
          </div>
        )}

        {/* Body — Members */}
        {activeTab === "members" && (
          <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={fieldStyle}>
              <label style={labelStyle}>Current members ({members.length})</label>
              {members.length === 0 && (
                <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0 }}>No members yet.</p>
              )}
              {members.map((u) => (
                <div key={u.id} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "7px 10px",
                  borderRadius: "var(--r-md)",
                  border: "1px solid var(--border-strong)",
                  background: "var(--bg-elev)",
                  fontSize: 13,
                }}>
                  <span style={{ color: "var(--text)" }}>{userDisplayName(u)}</span>
                  <button
                    onClick={() => removeMember.mutate(u.id)}
                    disabled={removeMember.isPending}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "#EF4444", padding: "2px 4px", borderRadius: 4, lineHeight: 1 }}
                    title="Remove member"
                  >
                    <XIcon size={14} />
                  </button>
                </div>
              ))}
            </div>

            {nonMembers.length > 0 && (
              <div style={fieldStyle}>
                <label style={labelStyle}>Add member</label>
                {nonMembers.map((u) => (
                  <div key={u.id} style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "7px 10px",
                    borderRadius: "var(--r-md)",
                    border: "1px solid var(--border)",
                    background: "var(--bg-elev)",
                    fontSize: 13,
                  }}>
                    <span style={{ color: "var(--text-muted)" }}>{userDisplayName(u)}</span>
                    <button
                      onClick={() => addMember.mutate(u.id)}
                      disabled={addMember.isPending}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "var(--c-accent-mint, #6EE7B7)", padding: "2px 4px", borderRadius: 4, lineHeight: 1, fontSize: 12, fontWeight: 600 }}
                      title="Add member"
                    >
                      + Add
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Body — Prompts */}
        {activeTab === "prompts" && (
          <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "0 0 4px" }}>
              Override Jinja2 prompt templates per project. Grayed-out = using the file default. Overridden prompts are highlighted.
            </p>
            {promptSlots.length === 0 && (
              <p style={{ fontSize: 12, color: "var(--text-muted)" }}>No prompt slots available.</p>
            )}
            {promptSlots.map((slot) => (
              <PromptSlotRow
                key={slot.slug}
                slot={slot}
                override={promptOverrides[slot.slug]}
                onSave={handlePromptSave}
                onReset={handlePromptReset}
              />
            ))}
          </div>
        )}

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
            {activeTab === "settings" && (
              <button className="btn btn-primary" onClick={handleSave} disabled={isPending}>
                {isPending ? t("savingSettings") : t("saveSettings")}
              </button>
            )}
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
  const [uploadProgress, setUploadProgress] = useState<{ done: number; total: number } | null>(null);
  const [docSearch, setDocSearch] = useState("");
  const [docPage, setDocPage] = useState(1);
  const [showNewForm, setShowNewForm] = useState(false);
  const DOC_PAGE_SIZE = 50;
  const [showSettings, setShowSettings] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: projectList = [], isLoading: projLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: projects.list,
    staleTime: 30_000,
  });

  const active = activeId ? projectList.find((p) => p.project_id === activeId) : projectList[0];
  const handleSetActive = (id: string) => { setActiveId(id); setDocPage(1); setDocSearch(""); };

  const { data: projectStats } = useQuery({
    queryKey: ["projectStats", active?.project_id],
    queryFn: () => documents.projectStats(active!.project_id),
    enabled: !!active,
    refetchInterval: 5000,
  });

  const { data: docPageData, isLoading: docLoading } = useQuery<DocumentsPage>({
    queryKey: ["documents", active?.project_id, docPage, DOC_PAGE_SIZE],
    queryFn: () => documents.listPage(active!.project_id, docPage, DOC_PAGE_SIZE),
    enabled: !!active,
    refetchInterval: (query) => {
      const data = query.state.data as DocumentsPage | undefined;
      if (!data) return false;
      const processing = data.items.some((d) => d.status !== "indexed" && d.status !== "failed");
      return processing ? 3000 : false;
    },
  });
  const docList = docPageData?.items ?? [];
  const docTotal = docPageData?.total ?? 0;
  const docTotalPages = Math.ceil(docTotal / DOC_PAGE_SIZE);


  const createProject = useMutation({
    mutationFn: (data: CreateProjectInput) => projects.create(data),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setActiveId(p.project_id);
      setActiveProjectId(p.project_id);
      setShowNewForm(false);
      setNewName("");
      setNewDesc("");
    },
  });

  const deleteProject = useMutation({
    mutationFn: (id: string) => projects.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });

  // The drop zone always looked multi-file; it silently uploaded only the first.
  // Files go up one at a time so a large batch does not open dozens of sockets.
  const uploadDoc = useMutation({
    mutationFn: async (files: File[]) => {
      for (const file of files) {
        setUploadProgress({ done: files.indexOf(file), total: files.length });
        await documents.upload(active!.project_id, file);
      }
      setUploadProgress(null);
    },
    onSettled: () => {
      setUploadProgress(null);
      qc.invalidateQueries({ queryKey: ["documents", active?.project_id] });
      qc.invalidateQueries({ queryKey: ["project-stats", active?.project_id] });
    },
  });

  const deleteDoc = useMutation({
    mutationFn: ({ projectId, docId }: { projectId: string; docId: string }) =>
      documents.delete(projectId, docId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents", active?.project_id] }),
  });

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragHover(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length) uploadDoc.mutate(files);
  }, [uploadDoc]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) uploadDoc.mutate(files);
    e.target.value = "";
  };

  const filteredDocs = docList.filter((d) =>
    !docSearch || d.filename.toLowerCase().includes(docSearch.toLowerCase())
  );

  const indexedCount = projectStats?.indexed_count ?? docList.filter((d) => d.status === "indexed").length;
  const failedCount = projectStats?.failed_count ?? docList.filter((d) => d.status === "failed").length;
  const totalChunks = projectStats?.total_chunks ?? docList.reduce((s, d) => s + (d.chunk_count ?? 0), 0);
  const displayTotal = projectStats?.total_documents ?? docTotal ?? docList.length;

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
              if (newName.trim()) createProject.mutate({ name: newName, description: newDesc });
            }}
          >
            <input
              autoFocus
              value={newName}
              onChange={(e) => { setNewName(e.target.value); createProject.reset(); }}
              placeholder={t("projectNamePlaceholder")}
              style={{
                padding: "8px 10px", borderRadius: "var(--r-md)",
                border: `1px solid ${createProject.isError ? "#EF4444" : "var(--border-strong)"}`,
                background: "var(--bg-elev)", color: "var(--text)", fontSize: 13,
              }}
            />
            {createProject.isError && (
              <div style={{ fontSize: 11, color: "#EF4444", paddingLeft: 2 }}>
                {createProject.error?.message ?? "Failed to create project"}
              </div>
            )}
            <input
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              placeholder={t("descriptionPlaceholder")}
              style={{
                padding: "8px 10px", borderRadius: "var(--r-md)", border: "1px solid var(--border)",
                background: "var(--bg-elev)", color: "var(--text)", fontSize: 12,
              }}
            />
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
              onClick={() => { handleSetActive(p.project_id); setActiveProjectId(p.project_id); }}
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
                <div className="adm-rail-sub">{active?.project_id === p.project_id ? displayTotal : "—"} {t("docCount")}</div>
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
                <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.txt,.md" style={{ display: "none" }} onChange={handleFileInput} />
              </div>
            </div>

            {/* Stats */}
            <div className="adm-stats stagger">
              <div className="adm-stat">
                <div className="adm-stat-l"><FileText size={16} /><span>{t("stats_docs")}</span></div>
                <div className="adm-stat-v">{displayTotal}</div>
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
                {uploadProgress && uploadProgress.total > 1 && ` ${uploadProgress.done + 1} / ${uploadProgress.total}`}
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
              {docTotalPages > 1 && (
                <div style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "12px 16px",
                  borderTop: "1px solid var(--border)",
                  fontSize: 13,
                }}>
                  <span style={{ color: "var(--text-muted)" }}>
                    {((docPage - 1) * DOC_PAGE_SIZE) + 1}–{Math.min(docPage * DOC_PAGE_SIZE, docTotal)} of {docTotal}
                  </span>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      className="btn"
                      style={{ padding: "4px 12px", fontSize: 12 }}
                      disabled={docPage <= 1}
                      onClick={() => setDocPage((p) => p - 1)}
                    >
                      ← Prev
                    </button>
                    <span style={{ padding: "4px 8px", color: "var(--text-muted)", fontSize: 12 }}>
                      {docPage} / {docTotalPages}
                    </span>
                    <button
                      className="btn"
                      style={{ padding: "4px 12px", fontSize: 12 }}
                      disabled={docPage >= docTotalPages}
                      onClick={() => setDocPage((p) => p + 1)}
                    >
                      Next →
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}

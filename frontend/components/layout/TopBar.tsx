"use client";
import { Moon, Sun, Settings, ChevronRight, Pin } from "lucide-react";
import { useTranslations } from "next-intl";
import { useUIStore } from "@/store";
import { Project } from "@/lib/api";

interface Props {
  project?: Project | null;
  convTitle?: string;
  pinned?: boolean;
  onSettingsOpen?: () => void;
}

function LocaleToggle() {
  const { locale, setLocale } = useUIStore();
  return (
    <button
      className="icon-btn"
      style={{ width: "auto", padding: "0 8px", fontSize: 12, fontWeight: 600, fontFamily: "var(--font-mono)", gap: 0 }}
      title={locale === "en" ? "Switch to Polish" : "Przełącz na angielski"}
      onClick={() => setLocale(locale === "en" ? "pl" : "en")}
    >
      {locale === "en" ? "PL" : "EN"}
    </button>
  );
}

export default function TopBar({ project, convTitle, pinned, onSettingsOpen }: Props) {
  const { theme, setTheme } = useUIStore();
  const t = useTranslations("topbar");

  return (
    <div className="chat-top">
      <div className="chat-top-l">
        <div className="chat-breadcrumb">
          {project && (
            <button className="btn-ghost chat-bc-item">
              <span
                className="chat-bc-init"
                style={{ background: (project.color ?? "#7DD3FC") + "30", color: project.color ?? "#7DD3FC" }}
              >
                {project.initials ?? project.name.slice(0, 2).toUpperCase()}
              </span>
              <span className="chat-bc-name">{project.name}</span>
            </button>
          )}
          {project && convTitle && <ChevronRight size={12} className="chat-bc-sep" />}
          {convTitle && <span className="chat-bc-title">{convTitle}</span>}
          {pinned && <button className={`icon-btn chat-bc-pin${pinned ? " pinned" : ""}`}><Pin size={13} /></button>}
        </div>
      </div>
      <div className="chat-top-r">
        <LocaleToggle />
        <button
          className="icon-btn"
          title={theme === "light" ? t("darkMode") : t("lightMode")}
          onClick={() => setTheme(theme === "light" ? "dark" : "light")}
        >
          {theme === "light" ? <Moon size={15} /> : <Sun size={15} />}
        </button>
        {onSettingsOpen && (
          <button className="icon-btn" title="Settings" onClick={onSettingsOpen}>
            <Settings size={15} />
          </button>
        )}
      </div>
    </div>
  );
}

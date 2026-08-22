"use client";
import { Moon, Sun, Settings, ChevronRight, Menu } from "lucide-react";
import { useTranslations } from "next-intl";
import { useUIStore } from "@/store";
import { Project } from "@/lib/api";

interface Props {
  project?: Project | null;
  convTitle?: string;
  onSettingsOpen?: () => void;
  onMenuOpen?: () => void;
}

function LocaleToggle() {
  const { locale, setLocale } = useUIStore();
  return (
    <button
      className="icon-btn"
      style={{ width: "auto", padding: "0 8px", fontSize: 12, fontWeight: 600, fontFamily: "var(--font-mono)", gap: 0 }}
      title={locale === "en" ? "Switch to Polish" : "Przełącz na angielski"}
      aria-label={locale === "en" ? "Switch to Polish" : "Przełącz na angielski"}
      onClick={() => setLocale(locale === "en" ? "pl" : "en")}
    >
      {locale === "en" ? "PL" : "EN"}
    </button>
  );
}

export default function TopBar({ project, convTitle, onSettingsOpen, onMenuOpen }: Props) {
  const { theme, setTheme } = useUIStore();
  const t = useTranslations("topbar");

  return (
    <div className="chat-top">
      <div className="chat-top-l">
        {onMenuOpen && (
          <button className="icon-btn chat-top-menu" onClick={onMenuOpen} aria-label={t("menu")}>
            <Menu size={17} />
          </button>
        )}
        <nav className="chat-breadcrumb" aria-label="Breadcrumb">
          {project && (
            <span className="chat-bc-item">
              <span
                className="chat-bc-init"
                style={{ background: (project.color ?? "#7DD3FC") + "30", color: project.color ?? "#7DD3FC" }}
                aria-hidden="true"
              >
                {project.initials ?? project.name.slice(0, 2).toUpperCase()}
              </span>
              <span className="chat-bc-name">{project.name}</span>
            </span>
          )}
          {project && convTitle && <ChevronRight size={12} className="chat-bc-sep" aria-hidden="true" />}
          {convTitle && <span className="chat-bc-title">{convTitle}</span>}
        </nav>
      </div>
      <div className="chat-top-r">
        <LocaleToggle />
        <button
          className="icon-btn"
          title={theme === "light" ? t("darkMode") : t("lightMode")}
          aria-label={theme === "light" ? t("darkMode") : t("lightMode")}
          onClick={() => setTheme(theme === "light" ? "dark" : "light")}
        >
          {theme === "light" ? <Moon size={15} /> : <Sun size={15} />}
        </button>
        {onSettingsOpen && (
          <button
            className="icon-btn"
            title={t("settings")}
            aria-label={t("settings")}
            onClick={onSettingsOpen}
          >
            <Settings size={15} />
          </button>
        )}
      </div>
    </div>
  );
}

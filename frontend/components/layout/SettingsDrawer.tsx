"use client";
import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { X, Sun, Moon, RotateCcw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useUIStore } from "@/store";

interface Props {
  open: boolean;
  onClose: () => void;
}

/**
 * Every preference here already had a store field, a `data-*` attribute on <html>
 * and CSS behind it — there was simply no way to reach any of it from the UI.
 */
type OptionRowProps<T extends string> = {
  label: string;
  value: T;
  options: ReadonlyArray<{ id: T; label: string }>;
  onChange: (v: T) => void;
  hint?: string;
};

function OptionRow<T extends string>({ label, value, options, onChange, hint }: OptionRowProps<T>) {
  return (
    <div className="set-row">
      <div className="set-row-label" id={`set-${label}`}>{label}</div>
      <div className="set-seg" role="radiogroup" aria-labelledby={`set-${label}`}>
        {options.map((o) => (
          <button
            key={o.id}
            role="radio"
            aria-checked={value === o.id}
            className={`set-seg-btn${value === o.id ? " set-seg-btn-active" : ""}`}
            onClick={() => onChange(o.id)}
          >
            {o.label}
          </button>
        ))}
      </div>
      {hint && <p className="set-row-hint">{hint}</p>}
    </div>
  );
}

const ACCENTS = ["blue", "mint", "navy", "lavender"] as const;

export default function SettingsDrawer({ open, onClose }: Props) {
  const t = useTranslations("settings");
  const s = useUIStore();
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  // Escape closes, and focus moves into the panel so keyboard users are not
  // left behind on the trigger button.
  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.stopPropagation(); onClose(); }
      if (e.key !== "Tab") return;
      const focusable = panelRef.current?.querySelectorAll<HTMLElement>(
        "button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])"
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open || typeof document === "undefined") return null;

  const reset = () => {
    s.setTheme("light");
    s.setAccent("blue");
    s.setDensity("comfortable");
    s.setFont("inter");
    s.setAnim("normal");
    s.setCitationLayout("cards");
  };

  return createPortal(
    <div className="set-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        className="set-panel"
        role="dialog"
        aria-modal="true"
        aria-label={t("title")}
        ref={panelRef}
      >
        <div className="set-head">
          <h2>{t("title")}</h2>
          <button ref={closeRef} className="icon-btn" onClick={onClose} aria-label={t("close")}>
            <X size={16} />
          </button>
        </div>

        <div className="set-body">
          <div className="set-section">{t("appearance")}</div>

          <OptionRow
            label={t("theme")}
            value={s.theme}
            onChange={s.setTheme}
            options={[
              { id: "light" as const, label: t("theme_light") },
              { id: "dark" as const, label: t("theme_dark") },
            ]}
          />

          <div className="set-row">
            <div className="set-row-label" id="set-accent">{t("accent")}</div>
            <div className="set-accents" role="radiogroup" aria-labelledby="set-accent">
              {ACCENTS.map((a) => (
                <button
                  key={a}
                  role="radio"
                  aria-checked={s.accent === a}
                  aria-label={t(`accent_${a}`)}
                  title={t(`accent_${a}`)}
                  className={`set-accent set-accent-${a}${s.accent === a ? " set-accent-active" : ""}`}
                  onClick={() => s.setAccent(a)}
                />
              ))}
            </div>
          </div>

          <OptionRow
            label={t("density")}
            value={s.density}
            onChange={s.setDensity}
            options={[
              { id: "comfortable" as const, label: t("density_comfortable") },
              { id: "compact" as const, label: t("density_compact") },
            ]}
          />

          <OptionRow
            label={t("font")}
            value={s.font}
            onChange={s.setFont}
            options={[
              { id: "inter" as const, label: t("font_inter") },
              { id: "poppins" as const, label: t("font_poppins") },
              { id: "plex" as const, label: t("font_plex") },
            ]}
          />

          <OptionRow
            label={t("motion")}
            value={s.anim}
            onChange={s.setAnim}
            hint={t("motionHint")}
            options={[
              { id: "off" as const, label: t("anim_off") },
              { id: "subtle" as const, label: t("anim_subtle") },
              { id: "normal" as const, label: t("anim_normal") },
              { id: "playful" as const, label: t("anim_playful") },
            ]}
          />

          <div className="set-section">{t("citations")}</div>
          <OptionRow
            label={t("citations")}
            value={s.citationLayout}
            onChange={s.setCitationLayout}
            options={[
              { id: "cards" as const, label: t("citations_cards") },
              { id: "sidebar" as const, label: t("citations_sidebar") },
              { id: "inline" as const, label: t("citations_inline") },
            ]}
          />

          <div className="set-section">{t("language")}</div>
          <OptionRow
            label={t("language")}
            value={s.locale}
            onChange={s.setLocale}
            options={[
              { id: "en" as const, label: "English" },
              { id: "pl" as const, label: "Polski" },
            ]}
          />
        </div>

        <div className="set-foot">
          <button className="btn-ghost set-reset" onClick={reset}>
            <RotateCcw size={13} /> {t("reset")}
          </button>
          <span className="set-foot-theme">
            {s.theme === "light" ? <Sun size={13} /> : <Moon size={13} />}
          </span>
        </div>
      </div>
    </div>,
    document.body
  );
}

"use client";
export const dynamic = "force-dynamic";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Stethoscope, Quote, Shield, Mail, Lock, Eye, EyeOff,
  ArrowRight, Activity, UserRound,
} from "lucide-react";
import { auth } from "@/lib/api";
import { saveToken, saveUser } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const t = useTranslations("register");
  const tLogin = useTranslations("login");

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) { setError(t("errorShort")); return; }
    if (password !== confirm) { setError(t("errorMismatch")); return; }
    setLoading(true);
    setError(null);
    try {
      await auth.register(email, password, firstName || undefined, lastName || undefined);
      const { access_token, refresh_token } = await auth.login(email, password);
      saveToken(access_token, refresh_token);
      const user = await auth.me();
      saveUser(user);
      router.replace("/chat/new");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-root">
      {/* LEFT — brand panel */}
      <div className="login-brand">
        <div className="login-brand-inner">
          <div className="login-logo">
            <Activity size={28} />
            <span>medRAG</span>
          </div>

          <div className="login-headline">
            <h1>{tLogin("brandHeadline").split("\n").map((line, i) => (
              <span key={i}>{line}{i === 0 && <br />}</span>
            ))}</h1>
            <p>{tLogin("brandSubhead")}</p>
          </div>

          <div className="login-feature-cards stagger">
            <div className="login-feat">
              <div className="login-feat-ic"><Stethoscope size={18} /></div>
              <div>
                <div className="login-feat-t">{tLogin("feat1Title")}</div>
                <div className="login-feat-s">{tLogin("feat1Desc")}</div>
              </div>
            </div>
            <div className="login-feat">
              <div className="login-feat-ic"><Quote size={18} /></div>
              <div>
                <div className="login-feat-t">{tLogin("feat2Title")}</div>
                <div className="login-feat-s">{tLogin("feat2Desc")}</div>
              </div>
            </div>
            <div className="login-feat">
              <div className="login-feat-ic"><Shield size={18} /></div>
              <div>
                <div className="login-feat-t">{tLogin("feat3Title")}</div>
                <div className="login-feat-s">{tLogin("feat3Desc")}</div>
              </div>
            </div>
          </div>

          <div className="login-foot">
            <span>{tLogin("version")}</span>
            <span className="login-dot" />
            <span>PL · EN · DE</span>
          </div>
        </div>

        <svg className="login-bg" viewBox="0 0 600 600" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeOpacity="0.10" strokeWidth="0.5" />
            </pattern>
            <radialGradient id="glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.18" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
            </radialGradient>
          </defs>
          <rect width="600" height="600" fill="url(#grid)" />
          <circle cx="450" cy="160" r="200" fill="url(#glow)" />
          <circle cx="120" cy="500" r="160" fill="url(#glow)" />
        </svg>
      </div>

      {/* RIGHT — form */}
      <div className="login-form-wrap">
        <form className="login-form scale-in" onSubmit={submit}>
          <div className="login-form-head">
            <div className="login-form-eyebrow">{t("eyebrow")}</div>
            <h2>{t("headline")}</h2>
            <p>{t("subhead")}</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <label className="login-field">
              <span>{t("firstNameLabel")}</span>
              <div className="login-input">
                <UserRound size={16} />
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder={t("firstNamePlaceholder")}
                  autoComplete="given-name"
                />
              </div>
            </label>
            <label className="login-field">
              <span>{t("lastNameLabel")}</span>
              <div className="login-input">
                <UserRound size={16} />
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder={t("lastNamePlaceholder")}
                  autoComplete="family-name"
                />
              </div>
            </label>
          </div>

          <label className="login-field">
            <span>{t("emailLabel")}</span>
            <div className="login-input">
              <Mail size={16} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("emailPlaceholder")}
                autoComplete="email"
                required
              />
            </div>
          </label>

          <label className="login-field">
            <span>{t("passwordLabel")}</span>
            <div className="login-input">
              <Lock size={16} />
              <input
                type={showPw ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="new-password"
                required
              />
              <button type="button" className="icon-btn login-eye" onClick={() => setShowPw(!showPw)}>
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </label>

          <label className="login-field">
            <span>{t("confirmLabel")}</span>
            <div className="login-input">
              <Lock size={16} />
              <input
                type={showConfirm ? "text" : "password"}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="••••••••"
                autoComplete="new-password"
                required
              />
              <button type="button" className="icon-btn login-eye" onClick={() => setShowConfirm(!showConfirm)}>
                {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </label>

          {error && <div className="login-error"><Shield size={13} />{error}</div>}

          <button type="submit" className="btn btn-primary login-submit" disabled={loading}>
            {loading ? (
              <><span className="login-spin" /><span>{t("submitting")}</span></>
            ) : (
              <><span>{t("submit")}</span><ArrowRight size={16} /></>
            )}
          </button>

          <div className="login-foot-small">
            {t("hasAccount")} <a href="/login">{t("login")}</a>
          </div>
        </form>
      </div>
    </div>
  );
}

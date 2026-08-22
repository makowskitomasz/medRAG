"use client";
export const dynamic = "force-dynamic";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Stethoscope, Quote, Shield, Mail, Lock, Eye, EyeOff,
  Check, ArrowRight, Activity,
} from "lucide-react";
import { auth } from "@/lib/api";
import { saveToken, saveUser } from "@/lib/auth";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const returnTo = params.get("returnTo") || "/chat/new";
  const t = useTranslations("login");

  // Demo credentials are opt-in via env so they never ship pre-filled by default.
  const [email, setEmail] = useState(process.env.NEXT_PUBLIC_DEMO_EMAIL ?? "");
  const [password, setPassword] = useState(process.env.NEXT_PUBLIC_DEMO_PASSWORD ?? "");
  const [showPw, setShowPw] = useState(false);
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) { setError(t("errorMissing")); return; }
    setLoading(true);
    setError(null);
    try {
      const { access_token, refresh_token } = await auth.login(email, password);
      saveToken(access_token, refresh_token, remember);
      const user = await auth.me();
      saveUser(user);
      router.replace(returnTo);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
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
            <h1>{t("brandHeadline").split("\n").map((line, i) => (
              <span key={i}>{line}{i === 0 && <br />}</span>
            ))}</h1>
            <p>{t("brandSubhead")}</p>
          </div>

          <div className="login-feature-cards stagger">
            <div className="login-feat">
              <div className="login-feat-ic"><Stethoscope size={18} /></div>
              <div>
                <div className="login-feat-t">{t("feat1Title")}</div>
                <div className="login-feat-s">{t("feat1Desc")}</div>
              </div>
            </div>
            <div className="login-feat">
              <div className="login-feat-ic"><Quote size={18} /></div>
              <div>
                <div className="login-feat-t">{t("feat2Title")}</div>
                <div className="login-feat-s">{t("feat2Desc")}</div>
              </div>
            </div>
            <div className="login-feat">
              <div className="login-feat-ic"><Shield size={18} /></div>
              <div>
                <div className="login-feat-t">{t("feat3Title")}</div>
                <div className="login-feat-s">{t("feat3Desc")}</div>
              </div>
            </div>
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
                autoComplete="current-password"
              />
              <button type="button" className="icon-btn login-eye" onClick={() => setShowPw(!showPw)}>
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </label>

          {error && <div className="login-error"><Shield size={13} />{error}</div>}

          <div className="login-row">
            <label className="login-check">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              <span className="login-check-box">{remember && <Check size={11} />}</span>
              <span>{t("remember")}</span>
            </label>
            {/* No password-reset flow exists yet; say so rather than linking nowhere. */}
            <span className="login-link login-link-muted" title={t("forgotHint")}>
              {t("forgot")}
            </span>
          </div>

          <button type="submit" className="btn btn-primary login-submit" disabled={loading}>
            {loading ? (
              <><span className="login-spin" /><span>{t("submitting")}</span></>
            ) : (
              <><span>{t("submit")}</span><ArrowRight size={16} /></>
            )}
          </button>

          <div className="login-foot-small">
            {t("noAccount")} <a href="/register">{t("register")}</a>
          </div>
        </form>

      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}

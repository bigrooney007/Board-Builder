import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";

const GoogleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
    <path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3l5.7-5.7C34.3 6.1 29.4 4 24 4 13 4 4 13 4 24s9 20 20 20 20-9 20-20c0-1.3-.1-2.6-.4-3.9z"/>
    <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.9 1.2 8 3l5.7-5.7C34.3 6.1 29.4 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>
    <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/>
    <path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C41 35.4 44 30.2 44 24c0-1.3-.1-2.6-.4-3.9z"/>
  </svg>
);

const Field = ({ label, type = "text", value, onChange, testId, autoComplete }) => (
  <label className="bfg-field">
    <span>{label} <b>*</b></span>
    <input type={type} value={value} autoComplete={autoComplete} onChange={(event) => onChange(event.target.value)} data-testid={testId} required />
  </label>
);

export default function GameAuthPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { member, loading, login, register } = useMemberAuth();
  const [mode, setMode] = useState(searchParams.get("mode") === "login" ? "login" : "signup");
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", password: "", confirm: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { document.title = "Create Your Account | Board Fundraising Game"; }, []);
  useEffect(() => { if (!loading && member) navigate("/game/start", { replace: true }); }, [loading, member, navigate]);

  const set = (key) => (value) => setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event) => {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      if (mode === "signup") {
        if (form.password !== form.confirm) { setError("Passwords do not match."); setBusy(false); return; }
        await register({ first_name: form.first_name, last_name: form.last_name, email: form.email, password: form.password, confirm_password: form.confirm });
      } else {
        await login(form.email, form.password);
      }
      navigate("/game/start");
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not complete this request. Please try again.");
      setBusy(false);
    }
  };

  const googleAuth = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/game/start";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <BfgShell>
      <main className="bfg-flow" data-testid="bfg-auth-page">
        <div className="bfg-card">
          <p className="bfg-eyebrow">Your Board Fundraising Game</p>
          <h1>{mode === "signup" ? "Create Your Account" : "Welcome Back"}</h1>
          <p style={{ marginTop: 10 }}>{mode === "signup" ? "Set up your account to build your organisation's Board Fundraising Game." : "Log in to continue setting up your Board Fundraising Game."}</p>
          <div className="bfg-auth-tabs" style={{ marginTop: 24 }}>
            <button type="button" className={mode === "signup" ? "active" : ""} onClick={() => { setMode("signup"); setError(""); }} data-testid="bfg-auth-signup-tab">Create Account</button>
            <button type="button" className={mode === "login" ? "active" : ""} onClick={() => { setMode("login"); setError(""); }} data-testid="bfg-auth-login-tab">Log In</button>
          </div>
          <button type="button" className="bfg-google-btn" onClick={googleAuth} data-testid="bfg-google-auth-btn">
            <GoogleIcon /> {mode === "signup" ? "Sign up with Google" : "Sign in with Google"}
          </button>
          <div className="bfg-divider">or with email</div>
          <form onSubmit={submit}>
            {mode === "signup" && (
              <>
                <Field label="First name" value={form.first_name} onChange={set("first_name")} testId="bfg-auth-first-name" autoComplete="given-name" />
                <Field label="Last name" value={form.last_name} onChange={set("last_name")} testId="bfg-auth-last-name" autoComplete="family-name" />
              </>
            )}
            <Field label="Email" type="email" value={form.email} onChange={set("email")} testId="bfg-auth-email" autoComplete="email" />
            <Field label="Password" type="password" value={form.password} onChange={set("password")} testId="bfg-auth-password" autoComplete={mode === "signup" ? "new-password" : "current-password"} />
            {mode === "signup" && (
              <Field label="Confirm password" type="password" value={form.confirm} onChange={set("confirm")} testId="bfg-auth-confirm-password" autoComplete="new-password" />
            )}
            {error && <p className="bfg-error" data-testid="bfg-auth-error">{error}</p>}
            <div className="bfg-form-actions">
              {mode === "login" ? <Link to="/forgot-password" data-testid="bfg-forgot-password-link" style={{ fontSize: 14 }}>Forgot your password?</Link> : <span />}
              <button className="bfg-btn bfg-btn-primary" type="submit" disabled={busy} data-testid="bfg-auth-submit">
                {busy ? "Please wait…" : mode === "signup" ? "Create My Account" : "Log In"}
              </button>
            </div>
          </form>
        </div>
      </main>
    </BfgShell>
  );
}

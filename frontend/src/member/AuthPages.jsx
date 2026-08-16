import React, { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { authText, authPagesText } from "../content/appContent";

const Field = ({ label, type = "text", value, onChange, testId, autoComplete }) => (
  <label className="field"><span>{label} <b>*</b></span><input type={type} value={value} autoComplete={autoComplete} onChange={(event) => onChange(event.target.value)} data-testid={testId} required /></label>
);

export const LoginPage = () => {
  const { login } = useMemberAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const rawNext = searchParams.get("next") || "";
  const nextPath = rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await login(email, password); navigate(nextPath || "/app"); }
    catch (err) { setError(err.response?.data?.detail || "Login failed. Please try again."); setBusy(false); }
  };
  return (
    <MemberShell>
      <main className="member-auth-page" data-testid="member-login-page">
        <form className="member-auth-card" onSubmit={submit}>
          <p className="eyebrow">Member access</p>
          <h1>{authText.h_logInToBoardBuilder}</h1>
          <Field label="Email" type="email" value={email} onChange={setEmail} testId="member-login-email" autoComplete="email" />
          <Field label="Password" type="password" value={password} onChange={setPassword} testId="member-login-password" autoComplete="current-password" />
          {error && <p className="submit-error" data-testid="member-login-error">{error}</p>}
          <button className="button" type="submit" disabled={busy} data-testid="member-login-submit">{busy ? "Logging in…" : "Log In"}</button>
          <p className="member-auth-links"><Link to="/forgot-password" data-testid="member-forgot-link">Forgot your password?</Link></p>
        </form>
      </main>
    </MemberShell>
  );
};

export const ForgotPasswordPage = () => {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const response = await memberApi.post("/members/forgot-password", { email, origin_url: window.location.origin });
      setMessage(response.data.message);
    } catch (err) { setError(err.response?.data?.detail || "We could not process this request."); }
    setBusy(false);
  };
  return (
    <MemberShell>
      <main className="member-auth-page" data-testid="member-forgot-page">
        <form className="member-auth-card" onSubmit={submit}>
          <p className="eyebrow">Password help</p>
          <h1>{authText.h_forgotYourPassword}</h1>
          <p>{authPagesText.enterYourAccountEmailAnd}</p>
          <Field label="Email" type="email" value={email} onChange={setEmail} testId="member-forgot-email" autoComplete="email" />
          {message && <p className="member-success" data-testid="member-forgot-success">{message}</p>}
          {error && <p className="submit-error">{error}</p>}
          <button className="button" type="submit" disabled={busy} data-testid="member-forgot-submit">{busy ? "Sending…" : "Send Reset Link"}</button>
          <p className="member-auth-links"><Link to="/login">Back to login</Link></p>
        </form>
      </main>
    </MemberShell>
  );
};

export const ResetPasswordPage = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    if (password !== confirm) { setError("Passwords do not match"); return; }
    setBusy(true); setError("");
    try {
      const response = await memberApi.post("/members/reset-password", { token, password, confirm_password: confirm });
      setMessage(response.data.message);
      setTimeout(() => navigate("/login"), 2200);
    } catch (err) { setError(err.response?.data?.detail || "We could not reset your password."); setBusy(false); }
  };
  return (
    <MemberShell>
      <main className="member-auth-page" data-testid="member-reset-page">
        <form className="member-auth-card" onSubmit={submit}>
          <p className="eyebrow">Password reset</p>
          <h1>{authText.h_chooseANewPassword}</h1>
          <Field label="New password" type="password" value={password} onChange={setPassword} testId="member-reset-password" autoComplete="new-password" />
          <Field label="Confirm new password" type="password" value={confirm} onChange={setConfirm} testId="member-reset-confirm" autoComplete="new-password" />
          {message && <p className="member-success" data-testid="member-reset-success">{message}</p>}
          {error && <p className="submit-error" data-testid="member-reset-error">{error}</p>}
          <button className="button" type="submit" disabled={busy} data-testid="member-reset-submit">{busy ? "Saving…" : "Reset Password"}</button>
        </form>
      </main>
    </MemberShell>
  );
};

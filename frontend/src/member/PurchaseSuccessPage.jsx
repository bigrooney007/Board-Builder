import React, { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { purchaseSuccessText, purchaseSuccessPageText } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const supportedEntry = (source, sessionId) => ({
  recruitment_supported_2997: "/app/board-recruitment/setup?supported=1",
  board_recommitment_supported_2497: `/board-recommitment/dashboard?session_id=${encodeURIComponent(sessionId)}&supported=1#recommitment-forms`,
  board_fundraising_game_supported_2997: "/game/setup?supported=1",
  strategic_planning_supported_2997: `/strategic-planning/dashboard?session_id=${encodeURIComponent(sessionId)}&supported=1#sp-meeting`,
}[source] || "");

export const PurchaseSuccessPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { member, loading, login, register, refresh } = useMemberAuth();
  const sessionId = new URLSearchParams(location.search).get("session_id") || "";
  const [paymentState, setPaymentState] = useState("checking");
  const [mode, setMode] = useState("register");
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", password: "", confirm_password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [claimed, setClaimed] = useState("");
  const [claimedSource, setClaimedSource] = useState("");
  const [guestPassword, setGuestPassword] = useState({ password: "", confirm_password: "" });
  const nextStep = useCallback((source) => ({
    recruitment_497: "/app/board-recruitment/setup",
    board_fundraising_game_497: "/game/setup",
    strategic_planning_497: `/strategic-planning/dashboard?session_id=${encodeURIComponent(sessionId)}#sp-meeting`,
    board_recommitment_497: `/board-recommitment/dashboard?session_id=${encodeURIComponent(sessionId)}#recommitment-forms`,
  }[source] || supportedEntry(source, sessionId)), [sessionId]);

  useEffect(() => {
    if (!sessionId) { setPaymentState("missing"); return undefined; }
    let attempts = 0;
    let timer;
    const poll = async () => {
      attempts += 1;
      try {
        const response = await axios.get(`${API}/payments/status/${sessionId}`);
        if (response.data.payment_status === "paid") { setPaymentState("paid"); return; }
        if (["failed", "expired"].includes(response.data.payment_status)) { setPaymentState("failed"); return; }
      } catch { /* keep polling */ }
      if (attempts < 8) timer = setTimeout(poll, 2500);
      else setPaymentState("timeout");
    };
    poll();
    return () => clearTimeout(timer);
  }, [sessionId]);

  useEffect(() => {
    const claim = async () => {
      if (paymentState !== "paid" || loading || !member || claimed) return;
      try {
        const response = await memberApi.post("/members/claim-purchase", { session_id: sessionId });
        setClaimed(response.data.claimed);
        setClaimedSource(response.data.claimed_source || "");
        await refresh();
        const destination = nextStep(response.data.claimed_source);
        if (destination && !["free_game_guest", "guided_guest"].includes(member.account_status)) {
          navigate(destination, { replace: true });
        } else if (response.data.claimed_source === "recruit_with_rooney_997") {
          navigate("/app/recruitment/self-guided/module/1");
        } else if (response.data.claimed_source === "direct_diy_board_recruitment_497" || response.data.claimed_source === "recruitment_campaign_diy_297") {
          navigate("/app/board-recruitment");
        } else if (response.data.claimed_source === "recruitment_selection_onboarding_297") {
          navigate("/app/recruitment/self-guided/module/4");
        } else if (response.data.claimed_source === "board_fix_system_497") {
          navigate(`/board-fix-intake?session_id=${sessionId}`);
        } else if (response.data.claimed_source === "direct_diy_board_reactivation_497") {
          navigate(`/board-reactivation-intake?session_id=${sessionId}`);
        } else if (response.data.claimed_source === "direct_diy_board_activation_497" || response.data.claimed_source === "activate_my_board_with_rooney_2997") {
          navigate(`/board-activation-intake?session_id=${sessionId}`);
        }
      } catch (err) { setError(err.response?.data?.detail || "We could not link this purchase to your account."); }
    };
    claim();
  }, [paymentState, loading, member, claimed, sessionId, refresh, navigate, nextStep]);

  const updateField = (name) => (event) => setForm((current) => ({ ...current, [name]: event.target.value }));

  const secureGuestAccount = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await memberApi.post("/members/complete-guest-account", guestPassword);
      await refresh();
      navigate(nextStep(claimedSource) || "/game/setup", { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || "We could not save your password. Please try again.");
      setBusy(false);
    }
  };

  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      let claimedNow = "";
      let claimedSource = "";
      if (mode === "register") {
        if (form.password !== form.confirm_password) throw new Error("Passwords do not match");
        const response = await register({ ...form, session_id: sessionId });
        claimedNow = response.claimed;
        claimedSource = response.claimed_source || "";
        setClaimed(claimedNow);
      } else {
        const response = await login(form.email, form.password, sessionId);
        claimedNow = response.claimed;
        claimedSource = response.claimed_source || "";
        setClaimed(claimedNow);
      }
      const destination = nextStep(claimedSource);
      if (destination) {
        navigate(destination, { replace: true });
      } else
      if (claimedSource === "direct_diy_board_recruitment_497" || claimedSource === "recruitment_campaign_diy_297") {
        navigate("/app/board-recruitment");
      } else if (claimedSource === "recruitment_selection_onboarding_297") {
        navigate("/app/recruitment/self-guided/module/4");
      } else if (claimedSource === "board_fix_system_497") {
        navigate(`/board-fix-intake?session_id=${sessionId}`);
      } else if (claimedSource === "direct_diy_board_reactivation_497") {
        navigate(`/board-reactivation-intake?session_id=${sessionId}`);
      } else if (claimedSource === "direct_diy_board_activation_497" || claimedSource === "activate_my_board_with_rooney_2997") {
        navigate(`/board-activation-intake?session_id=${sessionId}`);
      } else {
        navigate(claimedNow === "recruitment_self_guided" ? "/app/recruitment/self-guided/module/1" : claimedNow === "recruitment_basic" ? "/app/recruitment/basic/module/1" : "/app");
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "We could not complete this step.");
      setBusy(false);
    }
  };

  return (
    <MemberShell>
      <main className="member-auth-page purchase-success-page" data-testid="purchase-success-page">
        {paymentState === "checking" && <div className="member-auth-card" data-testid="purchase-checking"><h1>{purchaseSuccessText.h_confirmingYourPayment}</h1><p>{purchaseSuccessPageText.pleaseWaitWhileWeVerify}</p></div>}
        {paymentState === "missing" && <div className="member-auth-card"><h1>{purchaseSuccessText.h_missingPurchaseDetails}</h1><p>{purchaseSuccessPageText.weCouldNotFindA}</p><Link className="button" to="/">Return Home</Link></div>}
        {(paymentState === "failed" || paymentState === "timeout") && <div className="member-auth-card" data-testid="purchase-failed"><h1>{purchaseSuccessText.h_weCouldNotConfirmYour}</h1><p>{purchaseSuccessPageText.ifYouCompletedThePayment}</p></div>}
        {paymentState === "paid" && (
          <div className="member-auth-card wide" data-testid="purchase-paid">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Payment confirmed</p>
            {["free_game_guest", "guided_guest"].includes(member?.account_status) ? (
              <>
                <h1>Create Your Board Builder Account</h1>
                <p>Your payment is confirmed. Set a password, then we will open the next step of your process.</p>
                <form onSubmit={secureGuestAccount} className="member-auth-form">
                  <label className="field"><span>Password <b>*</b></span><input type="password" minLength={8}
                    value={guestPassword.password} onChange={(event) => setGuestPassword({ ...guestPassword, password: event.target.value })}
                    required data-testid="guest-password" /></label>
                  <label className="field"><span>Confirm password <b>*</b></span><input type="password" minLength={8}
                    value={guestPassword.confirm_password} onChange={(event) => setGuestPassword({ ...guestPassword, confirm_password: event.target.value })}
                    required data-testid="guest-confirm-password" /></label>
                  {error && <p className="submit-error" data-testid="guest-account-error">{error}</p>}
                  <button className="button" type="submit" disabled={busy || !claimed} data-testid="guest-account-submit">
                    {busy ? "Saving…" : claimed ? "CREATE ACCOUNT AND CONTINUE" : "LINKING YOUR PURCHASE…"}
                  </button>
                </form>
              </>
            ) : member ? (
              <>
                <h1>{purchaseSuccessText.h_yourPurchaseIsLinkedTo}</h1>
                <p>You are logged in as {member.email}.{claimed ? " Your program access is ready." : ""}</p>
                {error && <p className="submit-error">{error}</p>}
                <button className="button" onClick={() => navigate("/app")} data-testid="purchase-go-dashboard">{purchaseSuccessPageText.goToMyBoardBuilder}</button>
              </>
            ) : (
              <>
                <h1 data-testid="create-account-heading">{mode === "register" ? "Create Your Account To Continue" : "Log In To Continue"}</h1>
                <p>{mode === "register" ? "Your payment is confirmed. Create your account and we will open the next step you are ready to complete." : "Log in and we will link this purchase to your existing account."}</p>
                <form onSubmit={submit} className="member-auth-form">
                  {mode === "register" && (
                    <div className="two-col-fields">
                      <label className="field"><span>First name <b>*</b></span><input value={form.first_name} onChange={updateField("first_name")} required data-testid="register-first-name" /></label>
                      <label className="field"><span>Last name <b>*</b></span><input value={form.last_name} onChange={updateField("last_name")} required data-testid="register-last-name" /></label>
                    </div>
                  )}
                  <label className="field"><span>Email <b>*</b></span><input type="email" value={form.email} onChange={updateField("email")} required data-testid="register-email" /></label>
                  <label className="field"><span>Password <b>*</b></span><input type="password" value={form.password} onChange={updateField("password")} required minLength={8} data-testid="register-password" /></label>
                  {mode === "register" && <label className="field"><span>Confirm password <b>*</b></span><input type="password" value={form.confirm_password} onChange={updateField("confirm_password")} required data-testid="register-confirm-password" /></label>}
                  {error && <p className="submit-error" data-testid="purchase-account-error">{error}</p>}
                  <button className="button" type="submit" disabled={busy} data-testid="purchase-account-submit">{busy ? "Please wait…" : mode === "register" ? "Create My Account" : "Log In"}</button>
                </form>
                <p className="member-auth-links">
                  {mode === "register" ? (
                    <button type="button" className="link-button" onClick={() => { setMode("login"); setError(""); }} data-testid="switch-to-login">{purchaseSuccessPageText.alreadyHaveAnAccountLog}</button>
                  ) : (
                    <button type="button" className="link-button" onClick={() => { setMode("register"); setError(""); }} data-testid="switch-to-register">{purchaseSuccessPageText.needAnAccountCreateOne}</button>
                  )}
                </p>
              </>
            )}
          </div>
        )}
      </main>
    </MemberShell>
  );
};

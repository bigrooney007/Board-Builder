import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const VIDEO_ID = "6mveKNEOl9E";

const EXPLAINS = [
  "Reviewing the applicants your campaign brings in",
  "Selecting the applicants you want to move forward with",
  "Interviewing your applicants",
  "Completing reference checks",
  "Preparing your selected applicants for onboarding",
];

const INCLUDES = [
  "Tailored interview guides for your applicants",
  "Reference-check resources",
  "Onboarding materials",
  "Onboarding facilitation guide",
  "The recruitment communications you need for this stage",
];

export default function SelectionOfferPage() {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const cancelled = new URLSearchParams(window.location.search).get("checkout") === "cancelled";

  useEffect(() => { document.title = "Ready to Start Selection & Interviews? | Nonprofit Board Builder"; }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/login?next=/app/recruitment/selection-offer", { replace: true }); return; }
    if ((member.entitlements || []).includes("recruitment_selection_onboarding")) {
      navigate("/app/recruitment/self-guided/module/4", { replace: true });
    }
  }, [loading, member, navigate]);

  const startCheckout = async () => {
    setBusy(true); setNotice("");
    try {
      const response = await axios.post(`${API}/payments/selection-onboarding-checkout`, { origin_url: window.location.origin });
      window.location.href = response.data.checkout_url;
    } catch {
      setNotice("We could not start checkout. Please try again in a moment.");
      setBusy(false);
    }
  };

  if (loading || !member) {
    return <MemberShell><main className="member-page"><p>Loading…</p></main></MemberShell>;
  }

  return (
    <MemberShell>
      <main className="member-page selection-offer-page" data-testid="selection-offer-page">
        <header className="member-page-heading">
          <p className="eyebrow">Your Campaign Is Launched</p>
          <h1 data-testid="selection-offer-headline">Ready to Start Selection &amp; Interviews?</h1>
          <p data-testid="selection-offer-subtitle">As applicants begin coming in, here is what happens next.</p>
        </header>

        <div className="module-video" data-testid="selection-offer-video">
          <iframe src={`https://www.youtube.com/embed/${VIDEO_ID}`} title="Selection & Interviews" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
        </div>

        <section className="member-card" data-testid="selection-offer-explains">
          <h2>What happens after applicants begin coming in</h2>
          <ul className="selection-offer-list">
            {EXPLAINS.map((line) => <li key={line}><CheckCircle2 size={17} /> {line}</li>)}
          </ul>
        </section>

        <section className="member-card selection-offer-card" data-testid="selection-offer-card">
          <h2>Selection, Interview, Reference Check &amp; Onboarding</h2>
          <p className="selection-offer-price" data-testid="selection-offer-price">$297 <span>One Time</span></p>
          <p>Get access to the resources and guidance you need to select, interview, reference-check and onboard the board members you choose.</p>
          <ul className="selection-offer-list">
            {INCLUDES.map((line) => <li key={line}><CheckCircle2 size={17} /> {line}</li>)}
          </ul>
          {cancelled && !notice && <p className="submit-error" data-testid="selection-offer-cancelled">Your checkout was cancelled. You can start again whenever you are ready.</p>}
          {notice && <p className="submit-error" data-testid="selection-offer-error">{notice}</p>}
          <button className="button" onClick={startCheckout} disabled={busy} data-testid="selection-offer-buy-button">
            {busy ? "Starting Checkout…" : "Start Selection & Interviews — $297"}
          </button>
        </section>
      </main>
    </MemberShell>
  );
}

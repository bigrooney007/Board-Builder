import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "@/funnels/FunnelLayout";
import { useFlowVideo } from "@/hooks/useFlowVideos";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function WelcomePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const sessionId = new URLSearchParams(location.search).get("session_id") || "";
  const [paymentState, setPaymentState] = useState("checking");
  const video = useFlowVideo("post_payment_welcome");

  useEffect(() => { document.title = "Welcome | Fundraising Board Builder"; }, []);

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

  return (
    <FunnelLayout restrained>
      <main className="funnel-page" data-testid="fbb-welcome-page">
        {paymentState === "checking" && (
          <section className="member-card" data-testid="fbb-welcome-checking" style={{ textAlign: "center", marginTop: 40 }}>
            <h1>Confirming Your Payment</h1>
            <p>Please wait while we verify your payment with Stripe.</p>
          </section>
        )}
        {paymentState === "missing" && (
          <section className="member-card" data-testid="fbb-welcome-missing" style={{ textAlign: "center", marginTop: 40 }}>
            <h1>Missing Purchase Details</h1>
            <p>We could not find a purchase reference. If you just paid, please use the link Stripe returned you to.</p>
          </section>
        )}
        {(paymentState === "failed" || paymentState === "timeout") && (
          <section className="member-card" data-testid="fbb-welcome-failed" style={{ textAlign: "center", marginTop: 40 }}>
            <h1>We Could Not Confirm Your Payment</h1>
            <p>If you completed the payment, give it a moment and refresh this page. If the problem continues, contact us and we will get you set up.</p>
          </section>
        )}
        {paymentState === "paid" && (
          <>
            <header className="funnel-hero-banner" data-testid="fbb-welcome-hero">
              <p className="purchase-confirmed" style={{ justifyContent: "center", display: "flex", alignItems: "center", gap: 8 }}><CheckCircle2 size={20} /> Payment confirmed</p>
              <h1 data-testid="fbb-welcome-headline">Welcome to the Fundraising Board Builder</h1>
            </header>
            <div style={{ maxWidth: 860, margin: "0 auto", padding: "0 20px" }}>
              {video?.youtube_id ? (
                <div className="module-video" data-testid="fbb-welcome-video">
                  <iframe src={`https://www.youtube.com/embed/${video.youtube_id}`} title="Welcome from Rooney" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
                </div>
              ) : (
                <div className="offer-video-placeholder" data-testid="fbb-welcome-video-placeholder" style={{ padding: "48px 20px", textAlign: "center", border: "1px solid #d8ded9", borderRadius: 10 }}>
                  <p style={{ fontWeight: 700, margin: 0 }}>A Welcome Message From Rooney</p>
                  <span>Video coming soon</span>
                </div>
              )}
              <section className="member-card" data-testid="fbb-welcome-cta-card" style={{ textAlign: "center", marginTop: 28 }}>
                <h2>LET'S GET STARTED</h2>
                <p>Before we begin, tell us a little about your organization so we can personalize the tools and resources you will use throughout the process.</p>
                <button className="button" onClick={() => navigate(`/board-fix-intake?session_id=${sessionId}`)} data-testid="fbb-welcome-intake-button" style={{ justifyContent: "center" }}>
                  COMPLETE YOUR INTAKE FORM
                </button>
              </section>
            </div>
          </>
        )}
      </main>
    </FunnelLayout>
  );
}

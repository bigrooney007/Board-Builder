import { useState } from "react";
import axios from "axios";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { SITE_CONTENT } from "@/content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CHECKOUT_ENDPOINTS = {
  recruitment: { diy: "diy-checkout", dwy: "direct-project-checkout" },
  reactivation: { diy: "reactivation-diy-checkout", dwy: "reactivation-project-checkout" },
  activation: { diy: "activation-diy-checkout", dwy: "activation-project-checkout" },
};

export default function OfferVideoPage({ offer }) {
  const content = SITE_CONTENT.offerVideos[offer];
  const endpoints = CHECKOUT_ENDPOINTS[offer];
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");

  const startCheckout = async (choice) => {
    setBusy(choice);
    setNotice("");
    try {
      const response = await axios.post(`${API}/payments/${endpoints[choice]}`, { origin_url: window.location.origin });
      window.location.href = response.data.checkout_url;
    } catch {
      setNotice(SITE_CONTENT.offerVideos.checkoutError);
      setBusy("");
    }
  };

  return (
    <FunnelLayout restrained>
      <main data-testid={`offer-video-page-${offer}`} style={{ maxWidth: 900, margin: "0 auto", padding: "48px 20px" }}>
        <header style={{ marginBottom: 26, textAlign: "center" }}>
          <h1 className="video-page-title" data-testid={`offer-headline-${offer}`}>{content.headline}</h1>
        </header>

        <div className="video-stage" data-testid={`offer-video-${offer}`}>
          <span data-testid={`offer-video-placeholder-${offer}`}>{content.videoPlaceholder}</span>
        </div>

        <section data-testid={`offer-payment-choices-${offer}`}>
          <div className="offer-choice-grid">
            <button type="button" className="button" onClick={() => startCheckout("diy")} disabled={Boolean(busy)} data-testid={`offer-diy-button-${offer}`}>{busy === "diy" ? "Starting Checkout…" : content.diyLabel}</button>
            <button type="button" className="button button-outline" onClick={() => startCheckout("dwy")} disabled={Boolean(busy)} data-testid={`offer-dwy-button-${offer}`}>{busy === "dwy" ? "Starting Checkout…" : content.dwyLabel}</button>
          </div>
          {notice && <p className="submit-error" style={{ marginTop: 12 }} data-testid={`offer-checkout-error-${offer}`}>{notice}</p>}
        </section>

        <div style={{ marginTop: 40 }}>
          <TestimonialCarousel idPrefix={`offer-${offer}`} />
        </div>
      </main>
    </FunnelLayout>
  );
}

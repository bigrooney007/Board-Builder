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

const OfferCard = ({ offer, choice, card, busy, startingLabel, guarantee, onBuy }) => (
  <section className={`offer-sales-card ${choice}`} data-testid={`offer-${choice}-card-${offer}`}>
    <h2 data-testid={`offer-${choice}-heading-${offer}`}>{card.heading}</h2>
    {card.subheading && <p className="offer-sales-card-sub">{card.subheading}</p>}
    {card.price && <p className="offer-sales-price" data-testid={`offer-${choice}-price-${offer}`}>{card.price}</p>}
    {card.paragraphs.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
    <button type="button" className="button" onClick={() => onBuy(choice)} disabled={Boolean(busy)} data-testid={`offer-${choice}-button-${offer}`}>
      {busy === choice ? startingLabel : card.buttonLabel}
    </button>
    <p className="offer-sales-guarantee" data-testid={`offer-${choice}-guarantee-${offer}`}>{guarantee}</p>
  </section>
);

export default function OfferVideoPage({ offer }) {
  const shared = SITE_CONTENT.offerSalesPages;
  const content = shared[offer];
  const endpoints = CHECKOUT_ENDPOINTS[offer];
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");

  const startCheckout = async (choice) => {
    setBusy(choice);
    setNotice("");
    try {
      let resultToken = "";
      try { resultToken = sessionStorage.getItem("bt_result_token") || ""; } catch { /* storage is best-effort */ }
      const response = await axios.post(`${API}/payments/${endpoints[choice]}`, { origin_url: window.location.origin, result_token: resultToken });
      window.location.href = response.data.checkout_url;
    } catch {
      setNotice(shared.checkoutError);
      setBusy("");
    }
  };

  return (
    <FunnelLayout restrained>
      <main className="offer-sales-page" data-testid={`offer-sales-page-${offer}`}>
        <header className="funnel-hero-banner offer-sales-banner" data-testid={`offer-hero-${offer}`}>
          <h1 data-testid={`offer-headline-${offer}`}>{content.title}</h1>
          <p className="offer-sales-lead" data-testid={`offer-lead-${offer}`}>{content.lead}</p>
          <i aria-hidden="true" />
        </header>

        <div className="offer-sales-container">
          <article className="offer-sales-body" data-testid={`offer-sales-body-${offer}`}>
            {content.opening.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
            {content.sections.map((section) => (
              <section key={section.heading}>
                <h2>{section.heading}</h2>
                {section.paragraphs.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
              </section>
            ))}
          </article>

          <section className="offer-sales-offers" data-testid={`offer-payment-choices-${offer}`}>
            <div className="offer-sales-grid">
              <OfferCard offer={offer} choice="diy" card={content.diy} busy={busy} startingLabel={shared.startingCheckout} guarantee={shared.guarantee} onBuy={startCheckout} />
              <OfferCard offer={offer} choice="dwy" card={content.dwy} busy={busy} startingLabel={shared.startingCheckout} guarantee={shared.guarantee} onBuy={startCheckout} />
            </div>
            {notice && <p className="submit-error" style={{ marginTop: 12 }} data-testid={`offer-checkout-error-${offer}`}>{notice}</p>}
          </section>

          <div className="offer-sales-testimonials">
            <TestimonialCarousel idPrefix={`offer-${offer}`} />
          </div>

          <section className="offer-sales-closing" data-testid={`offer-closing-${offer}`}>
            <h2>{content.closing.heading}</h2>
            {content.closing.paragraphs.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
            {content.closing.showButtons && (
              <>
                <div className="offer-choice-grid">
                  <button type="button" className="button" onClick={() => startCheckout("diy")} disabled={Boolean(busy)} data-testid={`offer-closing-diy-button-${offer}`}>{busy === "diy" ? shared.startingCheckout : content.closing.diyLabel}</button>
                  <button type="button" className="button" onClick={() => startCheckout("dwy")} disabled={Boolean(busy)} data-testid={`offer-closing-dwy-button-${offer}`}>{busy === "dwy" ? shared.startingCheckout : content.closing.dwyLabel}</button>
                </div>
                <p className="offer-sales-guarantee" data-testid={`offer-closing-guarantee-${offer}`}>{shared.guarantee}</p>
              </>
            )}
          </section>
        </div>
      </main>
    </FunnelLayout>
  );
}

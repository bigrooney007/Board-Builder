import { useEffect, useState } from "react";
import axios from "axios";
import { FunnelLayout } from "./FunnelLayout";
import { BoardFixDiagnostic } from "./BoardFixDiagnostic";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { SITE_CONTENT } from "@/content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CHECKOUT_ENDPOINTS = {
  recruitment: { diy: "diy-checkout", dwy: "direct-project-checkout" },
  reactivation: { diy: "reactivation-diy-checkout", dwy: "reactivation-project-checkout" },
  activation: { diy: "activation-diy-checkout", dwy: "activation-project-checkout" },
  "board-fix": { diy: "board-fix-checkout", dwy: "board-fix-dwm-checkout" },
};

const CampaignLaunchOffer = ({ content, shared }) => {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const buy = async () => {
    setBusy(true); setError("");
    try {
      const response = await axios.post(`${API}/payments/campaign-launch-checkout`, { origin_url: window.location.origin, cancel_path: "/offer/recruitment" });
      window.location.href = response.data.checkout_url;
    } catch {
      setError(shared.checkoutError);
      setBusy(false);
    }
  };

  return (
    <section className="offer-sales-offers" data-testid="campaign-launch-offer">
      <div className="offer-sales-grid" style={{ gridTemplateColumns: "1fr" }}>
        <section className="offer-sales-card" data-testid="campaign-launch-card">
          <h2 data-testid="campaign-launch-outcome-heading">{content.outcomeHeading}</h2>
          <p data-testid="campaign-launch-outcome-body">Within <strong>48 to 72 hours after your campaign is launched</strong>, you should begin receiving applicants you can review, select and invite into conversations about joining your board.</p>
          <h2 data-testid="campaign-launch-guarantee-heading">{content.guaranteeHeading}</h2>
          <p data-testid="campaign-launch-guarantee-body">{content.guaranteeBody}</p>
          <p className="offer-sales-price" data-testid="campaign-launch-price">{content.price}</p>
          <button type="button" className="button" onClick={buy} disabled={busy} data-testid="campaign-launch-buy-button">
            {busy ? shared.startingCheckout : content.buttonLabel}
          </button>
          {error && <p className="submit-error" data-testid="campaign-launch-error">{error}</p>}
        </section>
      </div>
    </section>
  );
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

  useEffect(() => {
    if (!content.video) return;
    try {
      const key = `funnel_video_view_${offer}`;
      if (sessionStorage.getItem(key)) return;
      sessionStorage.setItem(key, "1");
    } catch { /* storage is best-effort */ }
    axios.post(`${API}/funnel-metrics/video-view`, { offer }).catch(() => {});
  }, [offer, content.video]);

  const startCheckout = async (choice) => {
    setBusy(choice);
    setNotice("");
    try {
      let resultToken = "";
      try {
        resultToken = sessionStorage.getItem("bt_result_token") || "";
        if (!resultToken) resultToken = JSON.parse(sessionStorage.getItem("funnelLeadContext") || "{}").result_token || "";
      } catch { /* storage is best-effort */ }
      const response = await axios.post(`${API}/payments/${endpoints[choice]}`, { origin_url: window.location.origin, result_token: resultToken, cancel_path: window.location.pathname });
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
          {!content.video && <p className="offer-sales-lead" data-testid={`offer-lead-${offer}`}>{content.lead}</p>}
          <i aria-hidden="true" />
        </header>

        {content.video || offer === "board-fix" ? (
          <div className="offer-sales-container">
            {content.video && (
            <div className="module-video offer-sales-video" data-testid={`offer-video-embed-${offer}`}>
              {content.video.youtubeId ? (
                <iframe src={`https://www.youtube.com/embed/${content.video.youtubeId}`} title={content.video.title} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
              ) : (
                <div className="offer-video-placeholder" data-testid={`offer-video-placeholder-${offer}`}><p>{content.video.title}</p><span>Video coming soon</span></div>
              )}
            </div>
            )}
            {offer === "board-fix" ? (
              <>
                <section className="offer-sales-body" data-testid="board-fix-foundation-section">
                  <h2 data-testid="board-fix-foundation-heading">{content.sectionHeading}</h2>
                  <p data-testid="board-fix-foundation-text"><strong>{content.sectionText}</strong></p>
                </section>
                <BoardFixDiagnostic />
              </>
            ) : offer === "recruitment" ? (
              <CampaignLaunchOffer content={content.campaignLaunch} shared={shared} />
            ) : (
            <section className="offer-sales-offers" data-testid={`offer-payment-choices-${offer}`}>
              {content.options ? (
                <div className="offer-sales-grid">
                  {Object.entries(content.options).map(([choice, card]) => (
                    <section key={choice} className={`offer-sales-card ${choice}`} data-testid={`offer-${choice}-card-${offer}`}>
                      <h2 data-testid={`offer-${choice}-heading-${offer}`}>{card.heading}</h2>
                      {card.regularPrice && <p className="offer-regular-price" data-testid={`offer-${choice}-regular-price-${offer}`}>Regular price: <s>{card.regularPrice}</s></p>}
                      <p className="offer-sales-price" data-testid={`offer-${choice}-price-${offer}`}>{card.price}</p>
                      {card.discountNote && <p className="offer-discount-note" data-testid={`offer-${choice}-discount-${offer}`}>{card.discountNote}</p>}
                      {card.paragraphs.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
                      <button type="button" className="button" onClick={() => startCheckout(choice)} disabled={Boolean(busy)} data-testid={`offer-${choice}-button-${offer}`}>
                        {busy === choice ? shared.startingCheckout : card.buttonLabel}
                      </button>
                      <p className="offer-sales-guarantee" data-testid={`offer-${choice}-guarantee-${offer}`}>{shared.guarantee}</p>
                    </section>
                  ))}
                </div>
              ) : (
                <>
                  <div className="offer-choice-grid">
                    <button type="button" className="button" onClick={() => startCheckout("diy")} disabled={Boolean(busy)} data-testid={`offer-diy-button-${offer}`}>{busy === "diy" ? shared.startingCheckout : content.videoButtons.diyLabel}</button>
                    {content.videoButtons.dwyLabel && <button type="button" className="button" onClick={() => startCheckout("dwy")} disabled={Boolean(busy)} data-testid={`offer-dwy-button-${offer}`}>{busy === "dwy" ? shared.startingCheckout : content.videoButtons.dwyLabel}</button>}
                  </div>
                  <p className="offer-sales-guarantee" data-testid={`offer-guarantee-${offer}`}>{shared.guarantee}</p>
                </>
              )}
              {notice && <p className="submit-error" style={{ marginTop: 12 }} data-testid={`offer-checkout-error-${offer}`}>{notice}</p>}
            </section>
            )}
            <div className="offer-sales-testimonials">
              <TestimonialCarousel idPrefix={`offer-${offer}`} />
            </div>
          </div>
        ) : (
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
        )}
      </main>
    </FunnelLayout>
  );
}

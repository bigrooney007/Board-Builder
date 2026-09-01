import { useEffect, useState } from "react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { SITE_CONTENT } from "@/content/siteContent";
import { startOfferCheckout } from "./BoardFixDiagnostic";

// Stable direct-entry offer pages. Presentation model: the Recruitment Campaign
// Launch page (/offer/recruitment) — Title → Video → Your Outcome → Guarantee →
// Price → CTA → Testimonials. Checkout reuses the existing diagnostic endpoints.
const OFFERS = {
  reactivation: {
    title: "Reactivate Your Board",
    videoTitle: "Board Reactivation Video",
    outcome: "Get your current Board Members to recommit and step up to their responsibilities, while helping those who are no longer able or willing to serve transition appropriately, so you know exactly what Board you have moving forward.",
    price: "$997",
    cta: "REACTIVATE MY BOARD — $997",
  },
  recruitment: {
    title: "Recruit the Board Your Nonprofit Needs",
    videoTitle: "Board Recruitment Video",
    outcome: "We will work with you to identify the Board Members your organization needs, launch your recruitment campaign, help you select the right candidates, and take them through appointment and onboarding so you can build the Board your nonprofit needs.",
    price: "$997",
    cta: "BUILD MY BOARD — $997",
  },
  activation: {
    title: "Activate Your Board to Raise Money",
    videoTitle: "Board Fundraising Activation Video",
    outcome: "We will work with you and your Board to build your Fundraising Strategy together, adopt it as your working fundraising plan, agree how each Board Member will participate, and equip your Board to begin raising money and building your organization's fundraising system.",
    price: "$997",
    cta: "ACTIVATE MY BOARD — $997",
  },
  complete_transformation: {
    title: "Complete Board Transformation",
    videoTitle: "Complete Board Transformation Video",
    outcome: "We will work with you to get your present Board to recommit and step up, recruit new Board Members to complement and strengthen your present Board, and activate both your current and new Board Members to start raising money and building your organization's fundraising system.",
    regular: "$3,997",
    discountNote: "50% Immediate-Action Discount",
    price: "$1,997",
    cta: "TRANSFORM MY BOARD — $1,997",
  },
};

const VIDEO_IDS = {
  complete_transformation: SITE_CONTENT.offerSalesPages["board-fix"].video.youtubeId,
};

export default function DirectOfferPage({ pathway }) {
  const offer = OFFERS[pathway];
  const shared = SITE_CONTENT.offerSalesPages;
  const videoId = VIDEO_IDS[pathway] || "";
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { document.title = `${offer.title} | Nonprofit Board Builder`; }, [offer.title]);

  const buy = async () => {
    setBusy(true); setError("");
    try {
      await startOfferCheckout(pathway);
    } catch {
      setError(shared.checkoutError);
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main className="offer-sales-page" data-testid={`direct-offer-page-${pathway}`}>
        <header className="funnel-hero-banner offer-sales-banner" data-testid={`direct-offer-hero-${pathway}`}>
          <h1 data-testid={`direct-offer-headline-${pathway}`}>{offer.title}</h1>
          <i aria-hidden="true" />
        </header>
        <div className="offer-sales-container">
          <div className="module-video offer-sales-video" data-testid={`direct-offer-video-${pathway}`}>
            {videoId ? (
              <iframe src={`https://www.youtube.com/embed/${videoId}`} title={offer.videoTitle} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
            ) : (
              <div className="offer-video-placeholder" data-testid={`direct-offer-video-placeholder-${pathway}`}><p>{offer.videoTitle}</p><span>Video coming soon</span></div>
            )}
          </div>
          <section className="offer-sales-offers" data-testid={`direct-offer-${pathway}`}>
            <div className="offer-sales-grid" style={{ gridTemplateColumns: "1fr" }}>
              <section className="offer-sales-card" data-testid={`direct-offer-card-${pathway}`}>
                <h2 data-testid={`direct-offer-outcome-heading-${pathway}`}>Your Outcome</h2>
                <p data-testid={`direct-offer-outcome-body-${pathway}`}><strong>{offer.outcome}</strong></p>
                <p className="offer-sales-guarantee" data-testid={`direct-offer-guarantee-${pathway}`}>{shared.guarantee}</p>
                {offer.regular && <p className="offer-regular-price" data-testid={`direct-offer-regular-price-${pathway}`}>Regular Investment: <s>{offer.regular}</s></p>}
                <p className="offer-sales-price" data-testid={`direct-offer-price-${pathway}`}>{offer.price}</p>
                {offer.discountNote && <p className="offer-discount-note" data-testid={`direct-offer-discount-${pathway}`}>{offer.discountNote}</p>}
                <button type="button" className="button" onClick={buy} disabled={busy} data-testid={`direct-offer-buy-button-${pathway}`}>
                  {busy ? shared.startingCheckout : offer.cta}
                </button>
                {error && <p className="submit-error" data-testid={`direct-offer-error-${pathway}`}>{error}</p>}
              </section>
            </div>
          </section>
          <div className="offer-sales-testimonials">
            <TestimonialCarousel idPrefix={`direct-offer-${pathway}`} />
          </div>
        </div>
      </main>
    </FunnelLayout>
  );
}

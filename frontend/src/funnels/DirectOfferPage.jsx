import { useEffect, useState } from "react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { SITE_CONTENT } from "@/content/siteContent";
import { startOfferCheckout } from "./BoardFixDiagnostic";

// Stable direct-entry offer pages. Presentation model: the Recruitment Campaign
// Launch page (/offer/recruitment) — Title → Video → Your Outcome → Price →
// CTA → Testimonials. Checkout reuses the existing diagnostic endpoints.
const OFFERS = {
  reactivation: {
    title: "Reactivate Your Board",
    videoId: "vXRlCDpPd1o", videoTitle: "Board Reactivation Video",
    outcome: "We will work with you to get your present Board Members to recommit and step up to their responsibilities, understand how each person is ready to contribute, and help those who can no longer continue transition respectfully.",
    regular: "$1,997",
    price: "$997",
    cta: "REACTIVATE MY BOARD — $997",
  },
  recruitment: {
    title: "Recruit The Board Your Nonprofit Needs",
    videoId: "4aLqppruUvs", videoTitle: "Board Recruitment Video",
    outcome: "We will work with you to identify the Board Members your organization needs, launch your recruitment campaign, select and interview the right applicants, complete the appointment process, and onboard your new Board Members.",
    regular: "$1,997",
    price: "$997",
    cta: "BUILD MY BOARD — $997",
  },
  activation: {
    title: "Activate Your Board For Fundraising",
    videoId: "Aw751ZtIIks", videoTitle: "Board Fundraising Activation Video",
    outcome: "We will work with you and your Board to build your Fundraising Strategy, adopt it together, agree how each Board Member will participate, and equip your Board to start raising money and building your organization's fundraising system.",
    regular: "$1,997",
    price: "$997",
    cta: "ACTIVATE MY BOARD — $997",
  },
  complete_transformation: {
    title: "Complete Board Transformation",
    videoId: "fJ5WDRMIC-w", videoTitle: "Complete Board Transformation Video",
    outcome: "We will work with you to get your present Board Members to recommit and step up, recruit the people your organization is missing, and activate both your current and new Board Members to raise money and build your organization's fundraising system.",
    regular: "$3,997",
    price: "$1,997",
    cta: "TRANSFORM MY BOARD — $1,997",
  },
};

export default function DirectOfferPage({ pathway }) {
  const offer = OFFERS[pathway];
  const shared = SITE_CONTENT.offerSalesPages;
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
            <iframe src={`https://www.youtube.com/embed/${offer.videoId}`} title={offer.videoTitle} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
          </div>
          <section className="offer-sales-offers" data-testid={`direct-offer-${pathway}`}>
            <div className="offer-sales-grid" style={{ gridTemplateColumns: "1fr" }}>
              <section className="offer-sales-card" data-testid={`direct-offer-card-${pathway}`}>
                <h2 data-testid={`direct-offer-outcome-heading-${pathway}`}>Your Outcome</h2>
                <p data-testid={`direct-offer-outcome-body-${pathway}`}><strong>{offer.outcome}</strong></p>
                <p className="offer-regular-price" data-testid={`direct-offer-regular-price-${pathway}`}>Regular Investment: <s>{offer.regular}</s></p>
                <p className="offer-sales-price" data-testid={`direct-offer-price-${pathway}`}>{offer.price}</p>
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

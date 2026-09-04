import { useEffect, useState } from "react";
import axios from "axios";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { SITE_CONTENT } from "@/content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// The two active recommendation/sales pages: Title -> Video -> Outcome -> Payment options -> Testimonials.
const OFFERS = {
  recruitment: {
    title: "Recruit the Board Your Nonprofit Needs",
    videoId: "4aLqppruUvs", videoTitle: "Board Recruitment Video",
    outcome: [
      "We will help you get the right Board Recruitment Campaign launched and begin bringing the right people into your recruitment process.",
      "We help your organization identify the Board Members it needs, prepare the recruitment campaign and the necessary recruitment materials, and launch the campaign.",
    ],
    options: [
      {
        key: "campaign", heading: "Launch My Board Recruitment Campaign", price: "$697",
        body: "We help you identify the Board Members your organization needs, prepare the recruitment campaign and necessary recruitment materials, and launch the campaign. The service ends at campaign launch.",
        cta: "LAUNCH MY BOARD RECRUITMENT CAMPAIGN — $697", endpoint: "campaign-launch-checkout",
      },
      {
        key: "rooney", heading: "Recruit My Board With Me", price: "$1,997",
        body: "Rooney works with you through the Board Recruitment process rather than only launching the campaign. After payment, you will complete your intake and be redirected to schedule a time with Rooney to begin.",
        cta: "RECRUIT MY BOARD WITH ROONEY — $1,997", endpoint: "direct-project-checkout",
      },
    ],
  },
  activation: {
    title: "Activate Your Board To Start Raising Money",
    videoId: "Aw751ZtIIks", videoTitle: "Board Fundraising Activation Video",
    outcome: [
      "You will work with your Board to build the Fundraising Strategy together, adopt it as your organization's working fundraising plan, agree how each Board Member will participate, and equip your Board with what it needs to begin executing.",
    ],
    options: [
      {
        key: "guided", heading: "Board Fundraising Activation", price: "$497",
        body: "The Guided Board Fundraising Activation System takes you and your Board through building the fundraising strategy together, adopting it, agreeing each Board Member's part and equipping your Board to execute.",
        cta: "ACTIVATE MY BOARD — $497", endpoint: "activation-diy-checkout",
      },
      {
        key: "rooney", heading: "Activate My Board With Rooney", price: "$2,997",
        body: "Rooney works directly with your organization and Board through the process. After payment, you will complete your intake and be redirected to schedule a time with Rooney to begin.",
        cta: "ACTIVATE MY BOARD WITH ROONEY — $2,997", endpoint: "activate-rooney-checkout",
      },
    ],
  },
};

const leadToken = () => {
  try { return JSON.parse(sessionStorage.getItem("funnelLeadContext") || "{}").result_token || ""; } catch { return ""; }
};

export default function DirectOfferPage({ pathway }) {
  const offer = OFFERS[pathway];
  const shared = SITE_CONTENT.offerSalesPages;
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { document.title = `${offer.title} | Nonprofit Board Builder`; }, [offer.title]);

  const buy = async (option) => {
    setBusy(option.key); setError("");
    try {
      const body = { origin_url: window.location.origin, result_token: leadToken(), cancel_path: window.location.pathname };
      const response = await axios.post(`${API}/payments/${option.endpoint}`, body);
      window.location.href = response.data.checkout_url;
    } catch {
      setError(shared.checkoutError);
      setBusy("");
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
          <article className="offer-sales-body" data-testid={`direct-offer-outcome-${pathway}`}>
            <h2 data-testid={`direct-offer-outcome-heading-${pathway}`}>Your Outcome</h2>
            {offer.outcome.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
          </article>
          <section className="offer-sales-offers" data-testid={`direct-offer-${pathway}`}>
            <div className="offer-sales-grid">
              {offer.options.map((option) => (
                <section className="offer-sales-card" key={option.key} data-testid={`direct-offer-${option.key}-card-${pathway}`}>
                  <h2 data-testid={`direct-offer-${option.key}-heading-${pathway}`}>{option.heading}</h2>
                  <p>{option.body}</p>
                  <p className="offer-sales-price" data-testid={`direct-offer-${option.key}-price-${pathway}`}>{option.price}</p>
                  <button type="button" className="button" onClick={() => buy(option)} disabled={Boolean(busy)} data-testid={`direct-offer-${option.key}-button-${pathway}`}>
                    {busy === option.key ? shared.startingCheckout : option.cta}
                  </button>
                </section>
              ))}
            </div>
            {error && <p className="submit-error" style={{ marginTop: 12 }} data-testid={`direct-offer-error-${pathway}`}>{error}</p>}
          </section>
          <div className="offer-sales-testimonials">
            <TestimonialCarousel idPrefix={`direct-offer-${pathway}`} />
          </div>
        </div>
      </main>
    </FunnelLayout>
  );
}

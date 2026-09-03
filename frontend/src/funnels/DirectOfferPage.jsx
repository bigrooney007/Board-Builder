import { useEffect, useState } from "react";
import axios from "axios";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { SITE_CONTENT } from "@/content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// The four recommendation/sales pages. Two offers each:
// A. Self-guided Complete Board Transformation — $497 (same product on all four pages)
// B. Work directly with Rooney — pathway-specific price.
const OFFERS = {
  reactivation: {
    title: "Your Current Board Needs to Be Reactivated",
    videoId: "vXRlCDpPd1o", videoTitle: "Board Reactivation Video",
    recommendation: "Based on your answers, your first priority should be getting your existing board members to step up, recommit, and take responsibility, while creating an appropriate path for those who are no longer able or willing to serve effectively to transition from the board.",
    why: "This is important because carrying inactive or disengaged board members prevents you from knowing the true strength of your board and can leave important responsibilities sitting with people who are no longer prepared to carry them.",
    how: "Watch the video below. I will show you the process I recommend for reactivating your board, how we help board members recommit and take responsibility, and the tools and materials you will receive to execute the process inside your organization.",
    begin: "Based on your answers, I recommend that you begin with Board Reactivation. You will still receive access to the complete process, so you can reactivate, recruit, and activate your board as your organization needs.",
    directBody: "We can work directly with your organization to execute the Board Reactivation process with you.",
    directLabel: "Board Reactivation", directPrice: "$2,997",
  },
  recruitment: {
    title: "Your Board Needs Strengthening Through Recruitment",
    videoId: "4aLqppruUvs", videoTitle: "Board Recruitment Video",
    recommendation: "Based on your answers, you need to strengthen your board by recruiting the right people with the expertise, experience, connections, and willingness to take responsibility for helping your organization move forward.",
    why: "Getting the right people into the right board positions is important because the strength of the people around your mission directly affects your organization's ability to raise money, build the right structures, make stronger decisions, and grow.",
    how: "Watch the video below. I will show you the process I recommend for strengthening your board, how we recruit the right people, and the tools and materials you will receive to execute the process inside your organization.",
    begin: "Based on your answers, I recommend that you begin with Board Recruitment. You will still receive access to the complete process, so you can reactivate, recruit, and activate your board as your organization needs.",
    directBody: "We can work directly with your organization to execute the Board Recruitment process with you and help you recruit the board you need.",
    directLabel: "Board Recruitment", directPrice: "$3,997",
  },
  activation: {
    title: "Your Board Needs to Be Activated for Fundraising",
    videoId: "Aw751ZtIIks", videoTitle: "Board Fundraising Activation Video",
    recommendation: "Based on your answers, your board may exist and even participate in the organization, but it has not yet been organized around a clear fundraising strategy and clear ways for Board Members to help raise money and build the organization's fundraising system.",
    why: "This is important because fundraising cannot continue sitting primarily with the founder or executive director when a capable board can help build the fundraising strategy, take ownership of the plan, and work with you to execute it.",
    how: "Watch the video below. I will show you the process I recommend for activating your board for fundraising, how we work with Board Members to build and adopt the fundraising strategy together, and the tools and resources you will receive to begin executing the plan.",
    begin: "Based on your answers, I recommend that you begin with Board Fundraising Activation. You will still receive access to the complete process, so you can reactivate, recruit, and activate your board as your organization needs.",
    directBody: "We can work directly with your organization and Board to build your fundraising strategy, adopt the plan together, determine how your Board Members will participate, and equip the Board to begin executing the fundraising plan.",
    directLabel: "Board Fundraising Activation", directPrice: "$4,997",
  },
  complete_transformation: {
    title: "Your Board Needs a Complete Transformation",
    videoId: "fJ5WDRMIC-w", videoTitle: "Complete Board Transformation Video",
    recommendation: "Based on your answers, the problem cannot be solved by recruitment, reactivation, or fundraising activation alone. Your board needs to be strengthened across the complete Reactivate → Recruit → Activate process.",
    why: "This is important because fixing only one part of your board can leave the underlying weaknesses in the other areas untouched.",
    how: "Watch the video below. I will show you how the Complete Board Transformation Process works, how we reactivate the people already on your Board, recruit the people you are missing, and activate the complete Board to raise money and work with you to build your organization.",
    begin: "Based on your answers, I recommend that you work through the Complete Board Transformation Process. You will receive the complete process to reactivate, recruit, and activate your board.",
    directBody: "We can work directly with your organization to lead the Complete Board Transformation Process with you — reactivating your present Board, recruiting the people you are missing, and activating the complete Board to begin raising money and building your organization's fundraising system.",
    directLabel: "Complete Board Transformation", directPrice: "$5,997",
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

  useEffect(() => { document.title = `${offer.directLabel} | Nonprofit Board Builder`; }, [offer.directLabel]);

  const buy = async (choice) => {
    setBusy(choice); setError("");
    try {
      const body = { origin_url: window.location.origin, result_token: leadToken(), cancel_path: window.location.pathname };
      let endpoint = "board-fix-checkout";
      if (choice === "direct") {
        if (pathway === "complete_transformation") endpoint = "board-fix-dwm-checkout";
        else { endpoint = "dfy-checkout"; body.pathway = pathway; }
      }
      const response = await axios.post(`${API}/payments/${endpoint}`, body);
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
          <article className="offer-sales-body" data-testid={`direct-offer-intro-${pathway}`}>
            <p><strong>{offer.recommendation}</strong></p>
            <p>{offer.why}</p>
            <section>
              <h2 data-testid={`direct-offer-how-heading-${pathway}`}>Here Is How to Fix It</h2>
              <p>{offer.how}</p>
            </section>
          </article>
          <div className="module-video offer-sales-video" data-testid={`direct-offer-video-${pathway}`}>
            <iframe src={`https://www.youtube.com/embed/${offer.videoId}`} title={offer.videoTitle} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
          </div>
          <section className="offer-sales-offers" data-testid={`direct-offer-${pathway}`}>
            <h2 style={{ textAlign: "center", fontWeight: 800, fontSize: "1.7rem" }} data-testid={`direct-offer-choose-heading-${pathway}`}>Choose How You Want to Fix Your Board</h2>
            <div className="offer-sales-grid">
              <section className="offer-sales-card" data-testid={`direct-offer-self-guided-card-${pathway}`}>
                <h2 data-testid={`direct-offer-self-guided-heading-${pathway}`}>Become Your Organization's Board Builder</h2>
                <p>Get access to the Complete Board Transformation Process and use the same system, tools, templates, scripts, resources, and guidance we use to help nonprofits build stronger boards.</p>
                <p>{offer.begin}</p>
                <p className="offer-regular-price" data-testid={`direct-offer-regular-price-${pathway}`}>Regular Price: <s>$997</s></p>
                <p className="offer-sales-price" data-testid={`direct-offer-price-${pathway}`}>Your 7-Day Discount Price: $497</p>
                <button type="button" className="button" onClick={() => buy("self")} disabled={Boolean(busy)} data-testid={`direct-offer-self-guided-button-${pathway}`}>
                  {busy === "self" ? shared.startingCheckout : "Equip Me to Fix My Board"}
                </button>
              </section>
              <section className="offer-sales-card" data-testid={`direct-offer-direct-card-${pathway}`}>
                <h2 data-testid={`direct-offer-direct-heading-${pathway}`}>Want Us to Do It for You?</h2>
                <p>{offer.directBody}</p>
                <p>After payment, you will complete your intake form and be redirected to schedule a time with Rooney to begin the process.</p>
                <p className="offer-sales-price" data-testid={`direct-offer-direct-price-${pathway}`}>{offer.directLabel}: {offer.directPrice}</p>
                <button type="button" className="button" onClick={() => buy("direct")} disabled={Boolean(busy)} data-testid={`direct-offer-direct-button-${pathway}`}>
                  {busy === "direct" ? shared.startingCheckout : "Do It for Me"}
                </button>
              </section>
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

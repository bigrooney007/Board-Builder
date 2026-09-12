import { useEffect, useState } from "react";
import axios from "axios";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { SITE_CONTENT } from "@/content/siteContent";
import { useFlowVideo } from "@/hooks/useFlowVideos";
import { CALENDLY_URL } from "./funnelConfig";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// The two active sales pages: Title -> Video -> Outcome -> Guided Execution offer ($497) -> (Recruitment only: $4,497 apply option) -> Testimonials.
const OFFERS = {
  recruitment: {
    title: "Recruit The Right Board Members For Your Organization",
    videoKey: "board_recruitment_offer", videoTitle: "Board Recruitment Video",
    outcome: [
      "Identify the exact type of board members your organization needs, launch your recruitment campaign, attract qualified applicants, select the right people and properly onboard your new board members using our proven recruitment process, tools and customized resources.",
    ],
    guidedHeading: "Board Recruitment Guided Execution",
    guidedParagraphs: [
      "Follow our proven board recruitment process with the strategy, tools, customized materials and guidance you need to launch your campaign, select the right people and properly onboard your new board members.",
      "The process helps your organization identify the skills and experience your board needs, create your recruitment materials, launch your board recruitment campaign, manage applicants, interview and select candidates, complete the appropriate reference or background checks and properly onboard your new board members.",
    ],
    cta: "START MY BOARD RECRUITMENT — $497",
  },
  activation: {
    title: "Build Your Fundraising System With Your Board",
    videoKey: "fundraising_activation_offer", videoTitle: "Board Fundraising Activation Video",
    outcome: [
      "Work with your board to identify your ideal funders, build your organization's fundraising strategy, agree how your board will participate, adopt the strategy together and equip each board member with what they need to begin executing.",
    ],
    guidedHeading: "Board Fundraising Activation Guided Execution",
    guidedParagraphs: [
      "Work through our guided process with your board to build the fundraising strategy and execution system your organization needs.",
      "You will collect the knowledge and ideas of your board members, bring those ideas together into your organization's fundraising strategy, review and adopt the strategy with your board, agree how each board member will participate and equip each participating board member with their own fundraising execution portfolio.",
    ],
    identifyHeading: "The process helps you identify:",
    identifyList: [
      "The individuals, businesses and grantors that are most likely to fund your mission",
      "Where to find them",
      "How to attract them",
      "The process your organization will use to raise money from them",
      "The people needed to execute the strategy",
      "The technology, tools and materials needed to support execution",
      "Your 90 to 120 day fundraising execution plan",
      "How your board members will participate in building and executing the system",
    ],
    cta: "BUILD OUR FUNDRAISING SYSTEM — $497",
  },
};

const APPLY_FIELDS = [
  { key: "name", label: "Name", type: "text" },
  { key: "email", label: "Email", type: "email" },
  { key: "phone", label: "Phone Number", type: "tel" },
  { key: "organization", label: "Organization Name", type: "text" },
  { key: "website", label: "Website", type: "text" },
];

const inputStyle = { width: "100%", padding: "11px 13px", borderRadius: 6, border: "1px solid #cfd6d2", fontSize: "1rem" };

const ApplyModal = ({ onClose }) => {
  const [form, setForm] = useState({ name: "", email: "", phone: "", organization: "", website: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (!form.name.trim() || !form.email.trim() || !form.phone.trim() || !form.organization.trim()) {
      setError("Please complete your name, email, phone number and organization name.");
      return;
    }
    setBusy(true);
    try {
      await axios.post(`${API}/recruit-with-rooney/apply`, form);
      window.location.href = CALENDLY_URL;
    } catch {
      setError("We could not submit your application. Please try again.");
      setBusy(false);
    }
  };

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 60, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <form className="member-card" data-testid="recruit-apply-modal" onClick={(e) => e.stopPropagation()} onSubmit={submit} style={{ maxWidth: 480, width: "100%", maxHeight: "88vh", overflowY: "auto" }}>
        <h2 style={{ marginTop: 0 }}>Recruit My Board With Rooney</h2>
        {APPLY_FIELDS.map((field) => (
          <label key={field.key} style={{ display: "block", marginBottom: 12 }}>
            <span style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>{field.label}</span>
            <input type={field.type} value={form[field.key]} onChange={(e) => setForm({ ...form, [field.key]: e.target.value })}
              data-testid={`recruit-apply-${field.key}-input`} style={inputStyle} />
          </label>
        ))}
        {error && <p className="submit-error" data-testid="recruit-apply-error">{error}</p>}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 6 }}>
          <button type="submit" className="button" disabled={busy} data-testid="recruit-apply-submit-button" style={{ justifyContent: "center" }}>
            {busy ? "Submitting…" : "APPLY AND BOOK MY CALL"}
          </button>
          <button type="button" className="button button-back" onClick={onClose} data-testid="recruit-apply-cancel-button">Cancel</button>
        </div>
      </form>
    </div>
  );
};

const leadToken = () => {
  try { return JSON.parse(sessionStorage.getItem("funnelLeadContext") || "{}").result_token || ""; } catch { return ""; }
};

export default function DirectOfferPage({ pathway }) {
  const offer = OFFERS[pathway];
  const shared = SITE_CONTENT.offerSalesPages;
  const video = useFlowVideo(offer.videoKey);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showApply, setShowApply] = useState(false);

  useEffect(() => { document.title = `${offer.title} | Nonprofit Board Builder`; }, [offer.title]);

  const buy = async () => {
    setBusy(true); setError("");
    try {
      const body = { origin_url: window.location.origin, result_token: leadToken(), cancel_path: window.location.pathname, product: pathway };
      const response = await axios.post(`${API}/payments/fundraising-board-builder-checkout`, body);
      window.location.href = response.data.checkout_url;
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
            {video?.youtube_id ? (
              <iframe src={`https://www.youtube.com/embed/${video.youtube_id}`} title={offer.videoTitle} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
            ) : (
              <div className="offer-video-placeholder" data-testid={`direct-offer-video-placeholder-${pathway}`}><p>{offer.videoTitle}</p><span>Video coming soon</span></div>
            )}
          </div>
          <article className="offer-sales-body" data-testid={`direct-offer-outcome-${pathway}`}>
            <h2 data-testid={`direct-offer-outcome-heading-${pathway}`}>Your Outcome</h2>
            {offer.outcome.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
          </article>
          <section className="offer-sales-offers" data-testid={`direct-offer-${pathway}`}>
            <section className="offer-sales-card" data-testid={`direct-offer-guided-card-${pathway}`}>
              <h2 data-testid={`direct-offer-guided-heading-${pathway}`}>{offer.guidedHeading}</h2>
              {offer.guidedParagraphs.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
              {offer.identifyList && (
                <>
                  <p><strong>{offer.identifyHeading}</strong></p>
                  <ul data-testid={`direct-offer-identify-list-${pathway}`}>
                    {offer.identifyList.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </>
              )}
              <p className="offer-sales-price" data-testid={`direct-offer-pricing-${pathway}`}>
                <span style={{ display: "block", fontSize: "1rem", fontWeight: 600, textDecoration: "line-through", opacity: 0.7 }}>Regular Price: $997</span>
                <span style={{ display: "block" }}>50% OFF FOR THE NEXT 7 DAYS: $497</span>
              </p>
              <button type="button" className="button" onClick={buy} disabled={busy} data-testid={`direct-offer-guided-button-${pathway}`}>
                {busy ? shared.startingCheckout : offer.cta}
              </button>
            </section>
            {pathway === "recruitment" && (
              <section className="offer-sales-card" data-testid="direct-offer-rooney-card-recruitment" style={{ marginTop: 22 }}>
                <h2 data-testid="direct-offer-rooney-heading-recruitment">Recruit My Board With Rooney</h2>
                <p>Want us to work directly with you through the recruitment process? Apply to work with Rooney and his team to identify the board your organization needs, launch your recruitment campaign, support your selection process and properly onboard your new board members.</p>
                <p className="offer-sales-price" data-testid="direct-offer-rooney-price-recruitment">$4,497</p>
                <button type="button" className="button" onClick={() => setShowApply(true)} data-testid="direct-offer-rooney-apply-button">
                  APPLY TO RECRUIT MY BOARD WITH ROONEY
                </button>
              </section>
            )}
            {error && <p className="submit-error" style={{ marginTop: 12 }} data-testid={`direct-offer-error-${pathway}`}>{error}</p>}
          </section>
          <div className="offer-sales-testimonials">
            <TestimonialCarousel idPrefix={`direct-offer-${pathway}`} />
          </div>
        </div>
      </main>
      {showApply && <ApplyModal onClose={() => setShowApply(false)} />}
    </FunnelLayout>
  );
}

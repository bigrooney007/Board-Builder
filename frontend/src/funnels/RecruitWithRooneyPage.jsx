import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import { PlayCircle, ShieldCheck, X } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { useReviewMode } from "@/reviewMode";
import { PAGE_META, usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TESTIMONIAL_PRIORITY = ["Pastor Cyrena Denniston", "Tony Barnes", "Martina Jones", "Devona Boone", "Donna Kargel"];

const toEmbedUrl = (url) => {
  const match = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/|live\/)|youtu\.be\/)([\w-]{6,})/);
  return match ? `https://www.youtube.com/embed/${match[1]}?rel=0` : url;
};

const GuaranteeTermsModal = ({ close }) => {
  const [terms, setTerms] = useState("");
  useEffect(() => {
    axios.get(`${API}/recruitment-guarantee`).then((response) => setTerms(response.data.terms)).catch(() => setTerms(""));
  }, []);
  return (
    <div className="guarantee-modal-overlay" onClick={close} data-testid="rwr-guarantee-modal-overlay">
      <div className="guarantee-modal" onClick={(event) => event.stopPropagation()} data-testid="rwr-guarantee-modal">
        <button className="guarantee-close" onClick={close} aria-label="Close" data-testid="rwr-guarantee-modal-close"><X size={20} /></button>
        <h3>Recruitment Guarantee Terms</h3>
        <p data-testid="rwr-guarantee-terms-text">{terms || "Loading…"}</p>
      </div>
    </div>
  );
};

export default function RecruitWithRooneyPage() {
  usePageMeta(...PAGE_META.recruitWithRooney);
  const location = useLocation();
  const reviewMode = useReviewMode();
  const cancelled = new URLSearchParams(location.search).get("checkout") === "cancelled";
  const [videoUrl, setVideoUrl] = useState("");
  const [guaranteeConfigured, setGuaranteeConfigured] = useState(false);
  const [showTerms, setShowTerms] = useState(false);
  const [ctaNotice, setCtaNotice] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/direct-recruitment/config`).then((response) => setVideoUrl((response.data.video_url || "").trim())).catch(() => {});
    axios.get(`${API}/recruitment-guarantee`).then((response) => setGuaranteeConfigured(Boolean(response.data.configured))).catch(() => {});
  }, []);

  const handleGetStarted = async () => {
    setBusy(true);
    setCtaNotice("");
    try {
      const response = await axios.post(
        `${API}/payments/rooney-checkout`,
        { origin_url: window.location.origin, internal_test: reviewMode },
        { withCredentials: true },
      );
      window.location.href = response.data.checkout_url;
    } catch (err) {
      setCtaNotice(err.response?.status === 403 ? "Enrollment opening shortly." : "We could not start checkout. Please try again in a moment.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main data-testid="rwr-page">
        <section className="funnel-hero-banner rwr-hero" data-testid="rwr-hero">
          <h1 data-testid="rwr-headline">Recruit the Board Members Your Nonprofit Needs in 2 Weeks</h1>
          <p className="funnel-hero-banner-supporting" data-testid="rwr-subheadline">Build your board with me.</p>
          <i aria-hidden="true" />
        </section>

        <section className="rwr-section rwr-video-section" data-testid="rwr-video-area">
          <div className="rwr-video-frame">
            {videoUrl ? (
              <iframe
                src={toEmbedUrl(videoUrl)}
                title="Recruit Your Board With Rooney"
                allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                data-testid="rwr-video-embed"
              />
            ) : (
              <div className="rwr-video-placeholder" data-testid="rwr-video-placeholder">
                <PlayCircle size={58} aria-hidden="true" />
                <p>Board Recruitment Video Coming Soon</p>
              </div>
            )}
          </div>
        </section>

        <section className="rwr-section rwr-guarantee" data-testid="rwr-guarantee-section">
          <ShieldCheck className="rwr-guarantee-icon" size={40} aria-hidden="true" />
          <h2 data-testid="rwr-guarantee-heading">100% Refund Guarantee</h2>
          <p data-testid="rwr-guarantee-copy">Your investment is protected by my 100% refund guarantee.</p>
          {guaranteeConfigured && (
            <button type="button" className="link-button rwr-terms-link" onClick={() => setShowTerms(true)} data-testid="rwr-guarantee-terms-link">View Guarantee Terms</button>
          )}
        </section>

        <section className="rwr-section rwr-offer" data-testid="rwr-offer-section">
          <p className="rwr-reference-price" data-testid="rwr-reference-price"><span className="rwr-reference-label">Standard Price</span><s>$2,497</s></p>
          <h2 className="rwr-action-price" data-testid="rwr-action-price">Take Action Today: $997</h2>
          {cancelled && <p className="rwr-cta-notice" data-testid="rwr-cancelled-notice">Your payment was not completed. You can get started whenever you're ready.</p>}
          <button type="button" className="button rwr-cta-button" onClick={handleGetStarted} disabled={busy} data-testid="rwr-cta-button">{busy ? "Preparing Checkout…" : "GET STARTED NOW — $997"}</button>
          {ctaNotice && <p className="rwr-cta-notice" data-testid="rwr-cta-notice">{ctaNotice}</p>}
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Leaders Have Said" idPrefix="rwr" priorityNames={TESTIMONIAL_PRIORITY} />
      </main>
      {showTerms && <GuaranteeTermsModal close={() => setShowTerms(false)} />}
    </FunnelLayout>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { PlayCircle, ShieldCheck, X } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";
import { SITE_CONTENT } from "@/content/siteContent";

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
  const [videoUrl, setVideoUrl] = useState("");
  const [guaranteeConfigured, setGuaranteeConfigured] = useState(false);
  const [showTerms, setShowTerms] = useState(false);

  useEffect(() => {
    axios.get(`${API}/direct-recruitment/config`).then((response) => setVideoUrl((response.data.video_url || "").trim())).catch(() => {});
    axios.get(`${API}/recruitment-guarantee`).then((response) => setGuaranteeConfigured(Boolean(response.data.configured))).catch(() => {});
  }, []);

  return (
    <FunnelLayout restrained>
      <main data-testid="rwr-page">
        <section className="funnel-hero-banner rwr-hero" data-testid="rwr-hero">
          <h1 data-testid="rwr-headline">{SITE_CONTENT.recruitWithRooney.headline}</h1>
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

        <section className="ar-offers rwr-offers" data-testid="rwr-offer-section">
          <h2 data-testid="rwr-offers-heading">Two Ways I Can Help You Recruit Your Board</h2>
          <p className="ar-offers-supporting" data-testid="rwr-offers-supporting">Choose the level of support that works best for you.</p>
          <div className="ar-offer-grid">
            <article className="ar-offer-card" data-testid="rwr-diy-card">
              <h3 data-testid="rwr-diy-heading">Recruit Your Board Yourself</h3>
              <p className="ar-offer-price" data-testid="rwr-diy-price">$497</p>
              <p className="ar-offer-copy" data-testid="rwr-diy-copy">Watch me run the process, follow what I do, use the execution materials we provide and reach out whenever you need help along the way.</p>
              <Link className="button" to="/recruit-your-board-yourself" data-testid="rwr-diy-button">DO IT YOURSELF — $497</Link>
            </article>
            <article className="ar-offer-card" data-testid="rwr-dwm-card">
              <h3 data-testid="rwr-dwm-heading">Recruit Your Board With Me</h3>
              <p className="ar-offer-price" data-testid="rwr-dwm-price"><s className="rwr-dwm-reference" data-testid="rwr-dwm-reference-price">$3,997</s> $1,997</p>
              <p className="ar-offer-copy" data-testid="rwr-dwm-copy">We handle the outreach, you decide who joins your board, and we help properly bring the people you select into your organization.</p>
              <Link className="button" to="/board-recruitment-proposal" data-testid="rwr-dwm-button">DO IT WITH ME — $1,997</Link>
            </article>
          </div>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Leaders Have Said" idPrefix="rwr" priorityNames={TESTIMONIAL_PRIORITY} />
      </main>
      {showTerms && <GuaranteeTermsModal close={() => setShowTerms(false)} />}
    </FunnelLayout>
  );
}

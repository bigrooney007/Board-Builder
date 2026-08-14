import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { PlayCircle, ShieldCheck } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";
import { SITE_CONTENT } from "@/content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const toEmbedUrl = (url) => {
  const match = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/|live\/)|youtu\.be\/)([\w-]{6,})/);
  return match ? `https://www.youtube.com/embed/${match[1]}?rel=0` : url;
};

export default function ReactivateWithRooneyPage() {
  usePageMeta(...PAGE_META.reactivateWithRooney);
  const [videoUrl, setVideoUrl] = useState("");

  useEffect(() => {
    axios.get(`${API}/direct-reactivation/config`).then((response) => setVideoUrl((response.data.video_url || "").trim())).catch(() => {});
  }, []);

  return (
    <FunnelLayout restrained>
      <main data-testid="rxr-page">
        <section className="funnel-hero-banner rwr-hero" data-testid="rxr-hero">
          <h1 data-testid="rxr-headline">{SITE_CONTENT.reactivateWithRooney.headline}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="rxr-subheadline">Get the Board Members who are ready to serve to stand up, take responsibility and help move the organization forward — and have the difficult conversations with those who are no longer prepared to carry Board responsibility.</p>
          <i aria-hidden="true" />
        </section>

        <section className="rwr-section rwr-video-section" data-testid="rxr-video-area">
          <div className="rwr-video-frame">
            {videoUrl ? (
              <iframe
                src={toEmbedUrl(videoUrl)}
                title="Reactivate Your Board With Rooney"
                allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                data-testid="rxr-video-embed"
              />
            ) : (
              <div className="rwr-video-placeholder" data-testid="rxr-video-placeholder">
                <PlayCircle size={58} aria-hidden="true" />
                <p>Board Reactivation Training Video Coming Soon</p>
              </div>
            )}
          </div>
        </section>

        <section className="ar-offers rwr-offers" data-testid="rxr-offer-section">
          <h2 data-testid="rxr-offers-heading">Two Ways I Can Help You Reactivate Your Board</h2>
          <p className="ar-offers-supporting" data-testid="rxr-offers-supporting">Choose the level of support that works best for you.</p>
          <div className="ar-offer-grid">
            <article className="ar-offer-card" data-testid="rxr-diy-card">
              <h3 data-testid="rxr-diy-heading">Do It Yourself</h3>
              <p className="ar-offer-price" data-testid="rxr-diy-price">$497</p>
              <p className="ar-offer-copy" data-testid="rxr-diy-copy">Follow the Board Reactivation process yourself, work through your current Board Members, have the conversations that need to happen, and give the people who stay clear responsibility for helping move the organization forward.</p>
              <Link className="button" to="/reactivate-your-board-yourself" data-testid="rxr-diy-button">REACTIVATE MY BOARD MYSELF — $497</Link>
            </article>
            <article className="ar-offer-card" data-testid="rxr-dwm-card">
              <h3 data-testid="rxr-dwm-heading">Do It With Me</h3>
              <p className="ar-offer-price" data-testid="rxr-dwm-price"><s className="rwr-dwm-reference" data-testid="rxr-dwm-reference-price">$3,997</s> $1,997</p>
              <p className="ar-offer-copy" data-testid="rxr-dwm-copy">Work directly with Rooney through the Board Reactivation process so you can identify who is ready to stand up, deal with the people who are no longer prepared to serve, and rebuild an active Board with clear areas of responsibility.</p>
              <Link className="button" to="/board-reactivation-proposal" data-testid="rxr-dwm-button">REACTIVATE MY BOARD WITH ROONEY — $1,997</Link>
            </article>
          </div>
        </section>

        <section className="rwr-section rwr-guarantee" data-testid="rxr-guarantee-section">
          <ShieldCheck className="rwr-guarantee-icon" size={40} aria-hidden="true" />
          <h2 data-testid="rxr-guarantee-heading">{SITE_CONTENT.shared.guaranteeHeading}</h2>
          <p data-testid="rxr-guarantee-copy">{SITE_CONTENT.shared.guaranteeSentence}</p>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Leaders Have Said" idPrefix="rxr" />
      </main>
    </FunnelLayout>
  );
}

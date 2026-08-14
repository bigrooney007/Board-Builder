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

export default function ActivateWithRooneyPage() {
  usePageMeta(...PAGE_META.activateWithRooney);
  const [videoUrl, setVideoUrl] = useState("");

  useEffect(() => {
    axios.get(`${API}/direct-activation/config`).then((response) => setVideoUrl((response.data.video_url || "").trim())).catch(() => {});
  }, []);

  return (
    <FunnelLayout restrained>
      <main data-testid="awr-page">
        <section className="funnel-hero-banner rwr-hero" data-testid="awr-hero">
          <h1 data-testid="awr-headline">{SITE_CONTENT.activateWithRooney.headline}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="awr-subheadline">Your Board should understand the fundraising direction, help build the plan, take ownership of the work and know exactly how they can help raise money for the organization. You can lead the process yourself with my guidance and tools, or I can work through the process with you.</p>
          <i aria-hidden="true" />
        </section>

        <section className="rwr-section rwr-video-section" data-testid="awr-video-area">
          <div className="rwr-video-frame">
            {videoUrl ? (
              <iframe
                src={toEmbedUrl(videoUrl)}
                title="Activate Your Board With Rooney"
                allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                data-testid="awr-video-embed"
              />
            ) : (
              <div className="rwr-video-placeholder" data-testid="awr-video-placeholder">
                <PlayCircle size={58} aria-hidden="true" />
                <p>Board Fundraising Activation Video Coming Soon</p>
              </div>
            )}
          </div>
        </section>

        <section className="ar-offers rwr-offers" data-testid="awr-offer-section">
          <h2 data-testid="awr-offers-heading">Two Ways I Can Help You Activate Your Board</h2>
          <p className="ar-offers-supporting" data-testid="awr-offers-supporting">Choose the level of support that works best for you.</p>
          <div className="ar-offer-grid">
            <article className="ar-offer-card" data-testid="awr-diy-card">
              <h3 data-testid="awr-diy-heading">Activate Your Board Yourself</h3>
              <p className="ar-offer-price" data-testid="awr-diy-price">$497</p>
              <p className="ar-offer-copy" data-testid="awr-diy-copy">Lead your Board through the complete fundraising activation process yourself, with the process, tools and support you need to move from Board disengagement in fundraising to Board ownership and execution — get the Board involved in building the fundraising plan, turn everyone's ideas into one fundraising strategy, bring the plan back to the Board for review, facilitate adoption, establish clear responsibility and equip Board Members with practical fundraising tools.</p>
              <Link className="button" to="/activate-your-board-yourself" data-testid="awr-diy-button">I WANT TO ACTIVATE MY BOARD MYSELF</Link>
            </article>
            <article className="ar-offer-card" data-testid="awr-dwm-card">
              <h3 data-testid="awr-dwm-heading">Activate Your Board With Rooney</h3>
              <p className="ar-offer-price" data-testid="awr-dwm-price">$2,497</p>
              <p className="ar-offer-copy" data-testid="awr-dwm-copy">Rooney works through the Board Fundraising Activation process with you so your organization does not have to figure out how to turn Board Members into fundraising participants alone — Board participation in planning, one fundraising strategy, Board review and adoption, clear ownership, practical execution, and a founder who is no longer carrying fundraising alone.</p>
              <Link className="button" to="/board-activation-proposal" data-testid="awr-dwm-button">I WANT ROONEY TO HELP ACTIVATE MY BOARD</Link>
            </article>
          </div>
        </section>

        <section className="rwr-section rwr-guarantee" data-testid="awr-guarantee-section">
          <ShieldCheck className="rwr-guarantee-icon" size={40} aria-hidden="true" />
          <h2 data-testid="awr-guarantee-heading">{SITE_CONTENT.shared.guaranteeHeading}</h2>
          <p data-testid="awr-guarantee-copy">{SITE_CONTENT.shared.guaranteeSentence}</p>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Leaders Have Said" idPrefix="awr" />
      </main>
    </FunnelLayout>
  );
}

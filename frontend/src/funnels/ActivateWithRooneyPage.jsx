import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { PlayCircle, ShieldCheck } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";
import { SITE_CONTENT, activateWithRooneyPageText } from "@/content/siteContent";

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
          <p className="funnel-hero-banner-supporting" data-testid="awr-subheadline">{activateWithRooneyPageText.yourBoardShouldUnderstandThe}</p>
          <i aria-hidden="true" />
        </section>

        <section className="rwr-section rwr-video-section" data-testid="awr-video-area">
          <div className="rwr-video-frame">
            {videoUrl ? (
              <iframe
                src={toEmbedUrl(videoUrl)}
                title={activateWithRooneyPageText.activateYourBoardWithRooney2}
                allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                data-testid="awr-video-embed"
              />
            ) : (
              <div className="rwr-video-placeholder" data-testid="awr-video-placeholder">
                <PlayCircle size={58} aria-hidden="true" />
                <p>{activateWithRooneyPageText.boardFundraisingActivationVideoComing}</p>
              </div>
            )}
          </div>
        </section>

        <section className="ar-offers rwr-offers" data-testid="awr-offer-section">
          <h2 data-testid="awr-offers-heading">{activateWithRooneyPageText.twoWaysICanHelp}</h2>
          <p className="ar-offers-supporting" data-testid="awr-offers-supporting">{activateWithRooneyPageText.chooseTheLevelOfSupport}</p>
          <div className="ar-offer-grid">
            <article className="ar-offer-card" data-testid="awr-diy-card">
              <h3 data-testid="awr-diy-heading">{activateWithRooneyPageText.activateYourBoardYourself}</h3>
              <p className="ar-offer-price" data-testid="awr-diy-price">$497</p>
              <p className="ar-offer-copy" data-testid="awr-diy-copy">{activateWithRooneyPageText.leadYourBoardThroughThe}</p>
              <Link className="button" to="/activate-your-board-yourself" data-testid="awr-diy-button">{activateWithRooneyPageText.iWantToActivateMy}</Link>
            </article>
            <article className="ar-offer-card" data-testid="awr-dwm-card">
              <h3 data-testid="awr-dwm-heading">{activateWithRooneyPageText.activateYourBoardWithRooney}</h3>
              <p className="ar-offer-price" data-testid="awr-dwm-price">$5,497</p>
              <p className="ar-offer-copy" data-testid="awr-dwm-copy">{activateWithRooneyPageText.rooneyWorksThroughTheBoard}</p>
              <Link className="button" to="/board-activation-proposal" data-testid="awr-dwm-button">{activateWithRooneyPageText.iWantRooneyToHelp}</Link>
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

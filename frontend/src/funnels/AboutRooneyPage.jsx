import { Link } from "react-router-dom";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";

const founderPhotoUrl = "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/ezw4nj2a_InShot_20260413_074422056%20%281%29.webp";

// Exact approved subtitle for the About Rooney banner.
const ABOUT_ROONEY_SUBTITLE = "Helping nonprofits build strong fundraising board.";

// Existing approved public call-booking link (same as the homepage "Book a Call With Rooney" button).
const BOOK_A_CALL_URL = "https://calendly.com/boardbuilder/recruitboard";

export default function AboutRooneyPage() {
  usePageMeta(...PAGE_META.aboutRooney);
  return (
    <FunnelLayout restrained>
      <main data-testid="about-rooney-page">
        <section className="funnel-hero-banner ar-hero" data-testid="about-rooney-hero">
          <div className="ar-hero-photo">
            <img src={founderPhotoUrl} alt="Rooney Akpesiri, The Nonprofit Board Builder" data-testid="about-rooney-photo" />
          </div>
          <div className="ar-hero-copy">
            <h1 data-testid="about-rooney-name">Rooney Akpesiri</h1>
            <p className="ar-hero-title" data-testid="about-rooney-title">The Nonprofit Board Builder</p>
            {ABOUT_ROONEY_SUBTITLE && (
              <p className="ar-hero-subtitle" data-testid="about-rooney-subtitle">{ABOUT_ROONEY_SUBTITLE}</p>
            )}
          </div>
          <i aria-hidden="true" />
        </section>

        <TestimonialCarousel idPrefix="about-rooney" />

        <section className="ar-offers" data-testid="about-rooney-offers-section">
          <h2 data-testid="about-rooney-offers-heading">Two Ways I Can Help You Recruit Your Board</h2>
          <p className="ar-offers-supporting" data-testid="about-rooney-offers-supporting">Choose the level of support that works best for you.</p>
          <div className="ar-offer-grid">
            <article className="ar-offer-card" data-testid="about-rooney-diy-card">
              <h3 data-testid="about-rooney-diy-heading">Do It Yourself</h3>
              <p className="ar-offer-price" data-testid="about-rooney-diy-price">$497</p>
              <p className="ar-offer-copy" data-testid="about-rooney-diy-copy">Watch me run the board recruitment process, follow what I do for your own organization, use the execution materials provided, and reach out for support whenever you need help along the way.</p>
              <p className="ar-offer-payment-line" data-testid="about-rooney-diy-payment-line">One payment.</p>
              <Link className="button" to="/recruit-your-board-yourself" data-testid="about-rooney-diy-button">I WANT TO RECRUIT MY BOARD MYSELF</Link>
            </article>
            <article className="ar-offer-card" data-testid="about-rooney-dwm-card">
              <h3 data-testid="about-rooney-dwm-heading">Do It With Me</h3>
              <p className="ar-offer-price" data-testid="about-rooney-dwm-price">$1,997</p>
              <p className="ar-offer-copy" data-testid="about-rooney-dwm-copy">We handle the outreach, you decide who joins your board, and we help properly bring the people you select into your organization.</p>
              <p className="ar-offer-payment-line" data-testid="about-rooney-dwm-payment-line">One project. One payment.</p>
              <Link className="button" to="/board-recruitment-proposal" data-testid="about-rooney-dwm-button">I WANT TO RECRUIT MY BOARD WITH ROONEY</Link>
            </article>
          </div>
        </section>

        <section className="ar-about" data-testid="about-rooney-story-section">
          <h2 data-testid="about-rooney-story-heading">Meet Rooney Akpesiri</h2>
          <p className="ar-about-subheading" data-testid="about-rooney-story-subheading">The Nonprofit Board Builder</p>
          <div className="ar-about-body" data-testid="about-rooney-story-body">
            <p>I'm Rooney. Known to many as the Nonprofit Board Builder.</p>
            <p>I started as a nonprofit founder many years ago, where I built my first board.</p>
            <p>I made mistakes, damaged relationships, learned from the experience, rebuilt my board, and eventually developed a process that worked.</p>
            <p>Since then, I have served on nonprofit boards, worked as a fundraising consultant, served as Vice President of a fundraising consulting firm working with nonprofits across the United States, trained hundreds of nonprofit founders and fundraisers, helped nonprofits strengthen their boards, and contributed to raising more than $5 million.</p>
            <p>Today, I teach, coach, and work directly with founders and executive directors so they do not make the mistakes I made, damage their relationships, or waste their time.</p>
          </div>
        </section>

        <section className="ar-book-call" data-testid="about-rooney-book-call-section">
          <h2 data-testid="about-rooney-book-call-heading">Want to Discuss Your Board With Me?</h2>
          <p className="ar-book-call-copy" data-testid="about-rooney-book-call-copy">If you want to talk through where your Board is today, what you are trying to build, and whether I can help, book a call with me and let's discuss it.</p>
          <a className="button" href={BOOK_A_CALL_URL} target="_blank" rel="noreferrer" data-testid="about-rooney-book-call-button">BOOK A CALL WITH ROONEY</a>
        </section>
      </main>
    </FunnelLayout>
  );
}

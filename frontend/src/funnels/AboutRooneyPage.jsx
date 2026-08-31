import { Link } from "react-router-dom";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";
import { SITE_CONTENT, aboutRooneyPageText } from "@/content/siteContent";

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
            <img src={founderPhotoUrl} alt={aboutRooneyPageText.rooneyAkpesiriTheNonprofitBoard} data-testid="about-rooney-photo" />
          </div>
          <div className="ar-hero-copy">
            <h1 data-testid="about-rooney-name">{SITE_CONTENT.aboutRooney.headline}</h1>
            <p className="ar-hero-title" data-testid="about-rooney-title">{aboutRooneyPageText.theNonprofitBoardBuilder}</p>
            {ABOUT_ROONEY_SUBTITLE && (
              <p className="ar-hero-subtitle" data-testid="about-rooney-subtitle">{ABOUT_ROONEY_SUBTITLE}</p>
            )}
            <p className="ar-hero-subtitle" data-testid="about-rooney-diagnostic-copy">{aboutRooneyPageText.answerFourShortQuestionsAbout}</p>
            <Link className="button" to="/board-transformation" data-testid="about-rooney-diagnostic-button">{aboutRooneyPageText.tellMeWhatMyBoard}</Link>
          </div>
          <i aria-hidden="true" />
        </section>

        <TestimonialCarousel idPrefix="about-rooney" />

        <section className="ar-offers" data-testid="about-rooney-offers-section">
          <h2 data-testid="about-rooney-offers-heading">Ready to Fix Your Board?</h2>
          <p className="ar-offers-supporting" data-testid="about-rooney-offers-supporting">Tell us about your board and what you want to achieve with your board and we'll show you what you need to do to transform your board and build a high-performing board.</p>
          <div className="ar-offer-grid" style={{ gridTemplateColumns: "1fr", maxWidth: 560, margin: "0 auto" }}>
            <article className="ar-offer-card" data-testid="about-rooney-transformation-card">
              <h3 data-testid="about-rooney-transformation-heading">Transform Your Board</h3>
              <p className="ar-offer-copy" data-testid="about-rooney-transformation-copy">Fix your present board, recruit the board members you need, and get your board raising money and building your organization with you — one complete process.</p>
              <Link className="button" to="/board-transformation" data-testid="about-rooney-transformation-button">TELL US ABOUT YOUR BOARD</Link>
            </article>
          </div>
        </section>

        <section className="ar-about" data-testid="about-rooney-story-section">
          <h2 data-testid="about-rooney-story-heading">Meet Rooney Akpesiri</h2>
          <p className="ar-about-subheading" data-testid="about-rooney-story-subheading">{aboutRooneyPageText.theNonprofitBoardBuilder2}</p>
          <div className="ar-about-body" data-testid="about-rooney-story-body">
            <p>{aboutRooneyPageText.imRooneyKnownToMany}</p>
            <p>{aboutRooneyPageText.iStartedAsANonprofit}</p>
            <p>{aboutRooneyPageText.iMadeMistakesDamagedRelationships}</p>
            <p>{aboutRooneyPageText.sinceThenIHaveServed}</p>
            <p>{aboutRooneyPageText.todayITeachCoachAnd}</p>
          </div>
        </section>

        <section className="ar-book-call" data-testid="about-rooney-book-call-section">
          <h2 data-testid="about-rooney-book-call-heading">{aboutRooneyPageText.wantToDiscussYourBoard}</h2>
          <p className="ar-book-call-copy" data-testid="about-rooney-book-call-copy">{aboutRooneyPageText.ifYouWantToTalk}</p>
          <a className="button" href={BOOK_A_CALL_URL} target="_blank" rel="noreferrer" data-testid="about-rooney-book-call-button">{aboutRooneyPageText.bookACallWithRooney}</a>
        </section>
      </main>
    </FunnelLayout>
  );
}

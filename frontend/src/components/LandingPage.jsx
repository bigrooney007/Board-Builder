import { ArrowRight } from "lucide-react";
import { TestimonialsSection } from "@/components/TestimonialsSection";
import { FounderStorySection } from "@/components/FounderStorySection";
import { BlogSlider } from "@/pages/BlogPages";
import { SITE_CONTENT, landingPageText } from "@/content/siteContent";

const logoUrl = "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/2qaqmobl_Minimalist%20nonprofit%20logo%20design.png";

const home = SITE_CONTENT.home;

const OfferChoices = ({ location }) => (
  <div className={`offer-choices ${location}`} data-testid={`${location}-offer-choices`}>
    <a className="button" href="/reactivate" data-testid={`${location}-reactivate-button`}>{home.finalCta.reactivateButton}</a>
    <a className="button" href="/recruit" data-testid={`${location}-recruit-button`}>{home.finalCta.recruitButton}</a>
    <a className="button" href="/activate" data-testid={`${location}-activate-button`}>{home.finalCta.activateButton}</a>
  </div>
);

export const LandingPage = ({ onJoin }) => (
  <main data-testid="landing-page">
    <nav className="site-nav" data-testid="site-navigation">
      <a className="brand" href="#top" data-testid="brand-logo-link"><img src={logoUrl} alt={landingPageText.nonprofitBoardBuilder} data-testid="brand-logo-image" /></a>
      <div className="nav-links">
        <a href="#success-stories" data-testid="success-stories-link">{home.nav.successStories}</a>
        <a href="#my-story" data-testid="my-story-link">{home.nav.myStory}</a>
        <button onClick={onJoin} className="nav-text-button" data-testid="join-board-nav-link">{home.nav.joinABoard}</button>
      </div>
      <div className="nav-offer-buttons" data-testid="navigation-offer-choices"><a href="/reactivate">{home.nav.reactivate}</a><a href="/recruit">{home.nav.recruit}</a><a href="/activate">{home.nav.activate}</a><a href="/login" data-testid="nav-login-link">{home.nav.logIn}</a></div>
    </nav>

    <section id="top" className="hero-banner" data-testid="hero-section">
      <div className="hero-banner-inner">
        <h1 data-testid="hero-headline">{home.heroTitle}</h1>
        <p className="hero-banner-lead" data-testid="hero-supporting-text">{home.heroSubtitle}</p>
        <p style={{ marginTop: 22 }}><a className="button button-light" href="/board-fix" data-testid="hero-board-transformation-button">{home.cta}</a></p>
      </div>
    </section>

    <section className="home-intro" data-testid="home-intro-section">
      {home.boardFixHeadings.map((heading, index) => <h2 className="home-intro-heading" key={index} data-testid={`home-intro-heading-${index + 1}`}>{heading}</h2>)}
      {home.boardFixIntro.map((paragraph, index) => <p key={index} data-testid={`home-intro-paragraph-${index + 1}`}>{paragraph}</p>)}
      <p className="home-includes-lead" data-testid="home-includes-lead">{home.boardFixIncludesLead}</p>
      <ol className="home-includes-list" data-testid="home-includes-list">
        {home.boardFixIncludes.map((item, index) => <li key={index} data-testid={`home-includes-item-${index + 1}`}>{item}</li>)}
      </ol>
      {home.boardFixAfterIncludes.map((paragraph, index) => <p key={index} data-testid={`home-intro-after-paragraph-${index + 1}`}>{paragraph}</p>)}
    </section>

    <section className="section home-how" data-testid="home-how-section">
      <h2 data-testid="home-how-heading">{home.boardFixHowHeading || home.howHeading}</h2>
      {(home.boardFixHowParagraphs || home.howParagraphs).map((paragraph, index) => <p key={index} data-testid={`home-how-paragraph-${index + 1}`}>{paragraph}</p>)}
      <p style={{ marginTop: 18 }}><a className="button" href="/board-fix" data-testid="home-how-cta-button">{home.cta}</a></p>
    </section>

    <TestimonialsSection />

    <FounderStorySection />

    <section className="final-cta" data-testid="final-call-to-action"><p className="eyebrow" data-testid="final-cta-eyebrow">{home.finalCta.eyebrow}</p><h2 data-testid="final-cta-heading">{home.finalCta.heading}</h2><OfferChoices location="final" /></section>

    <BlogSlider />

    <section className="join-network-cta" data-testid="homepage-join-board-section"><div><p className="eyebrow light">{home.joinNetwork.eyebrow}</p><h2>{home.joinNetwork.heading}</h2><p>{home.joinNetwork.text}</p></div><button className="button button-light" onClick={onJoin} data-testid="homepage-join-network-button">{home.joinNetwork.button} <ArrowRight size={18} /></button></section>

    <footer id="footer" className="footer" data-testid="site-footer"><a className="brand footer-brand" href="#top" data-testid="footer-brand-link"><img src={logoUrl} alt={landingPageText.nonprofitBoardBuilder2} data-testid="footer-brand-logo-image" /></a><p data-testid="footer-statement">{home.footer.statement}</p><div className="footer-links"><a href="#top" data-testid="footer-about-link">{home.footer.about}</a><a href="#footer" data-testid="footer-contact-link">{home.footer.contact}</a><a href="/privacy-policy" data-testid="footer-privacy-link">{home.footer.privacy}</a><a href="/terms" data-testid="footer-terms-link">{home.footer.terms}</a></div></footer>
  </main>
);

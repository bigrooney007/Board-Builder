import { ArrowRight, Check, RefreshCcw, Rocket, Users } from "lucide-react";
import { TestimonialsSection } from "@/components/TestimonialsSection";
import { FounderStorySection } from "@/components/FounderStorySection";

const logoUrl = "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/2qaqmobl_Minimalist%20nonprofit%20logo%20design.png";

const stages = [
  { number: "01", icon: RefreshCcw, title: "Reactivate Your Present Board", text: "Identify the board members who can be recommitted, re-engaged and given meaningful responsibilities based on their strengths, experience and relationships.", button: "Reactivate My Board", path: "/reactivate" },
  { number: "02", icon: Users, title: "Recruit the Board Members You Are Missing", text: "Identify and recruit people with the fundraising experience, professional skills and networks required to complement your present board.", button: "Recruit My Board", path: "/recruit" },
  { number: "03", icon: Rocket, title: "Activate Your Board to Start Raising Money", text: "Help present and new board members take responsibility for fundraising in their areas of strength while contributing to the strategy, team, materials and consistent execution required to raise money.", button: "Activate My Board to Raise Money", path: "/activate" },
];

const discoveries = [
  ["Which Present Board Members Can Be Reactivated", "Identify the people who still believe in the mission and can become active again with clear expectations, responsibility and support."],
  ["Which Board Members May Need to Step Down", "Recognize when inactive, disruptive or uncommitted board members are preventing the board from moving forward."],
  ["The Exact Board Members You Need to Recruit", "Identify the skills, experience, relationships and fundraising capacity missing from the present board."],
  ["How to Activate the Board Around Fundraising", "Give every board member a clear role based on what they know, who they know and what they can confidently help the organization execute."],
  ["What Fundraising System the Board Must Help Build", "Determine whether the organization needs a fundraising strategy, fundraising team, fundraising materials or stronger execution."],
  ["The Best Way to Transform the Board", "Determine whether the organization needs guidance, one-on-one support or complete help executing the board transformation."],
];

const OfferChoices = ({ location }) => <div className={`offer-choices ${location}`} data-testid={`${location}-offer-choices`}><a className="button" href="/reactivate" data-testid={`${location}-reactivate-button`}>Reactivate My Board</a><a className="button" href="/recruit" data-testid={`${location}-recruit-button`}>Recruit My Board</a><a className="button" href="/activate" data-testid={`${location}-activate-button`}>Activate My Board to Raise Money</a></div>;

export const LandingPage = ({ onJoin }) => (
  <main data-testid="landing-page">
    <nav className="site-nav" data-testid="site-navigation">
      <a className="brand" href="#top" data-testid="brand-logo-link"><img src={logoUrl} alt="Nonprofit Board Builder" data-testid="brand-logo-image" /></a>
      <div className="nav-links">
        <a href="#how-it-works" data-testid="how-it-works-link">How It Works</a>
        <a href="#what-we-fix" data-testid="what-we-fix-link">What We Help You Fix</a>
        <a href="#tools-materials" data-testid="tools-materials-link">Tools and Materials</a>
        <a href="#success-stories" data-testid="success-stories-link">Success Stories</a>
        <a href="#my-story" data-testid="my-story-link">My Story</a>
        <button onClick={onJoin} className="nav-text-button" data-testid="join-board-nav-link">Join a Board</button>
        <a href="#how-it-works" data-testid="board-solutions-link">Board Solutions</a>
      </div>
      <div className="nav-offer-buttons" data-testid="navigation-offer-choices"><a href="/reactivate">Reactivate</a><a href="/recruit">Recruit</a><a href="/activate">Activate</a></div>
    </nav>

    <section id="top" className="hero" data-testid="hero-section">
      <div className="hero-copy">
        <p className="eyebrow" data-testid="hero-eyebrow">Your mission needs more than a board on paper</p>
        <h1 data-testid="hero-headline">Build the Powerhouse <em>Fundraising Board</em> Your Nonprofit Needs to Succeed</h1>
        <p className="hero-lead" data-testid="hero-supporting-text">Tell us about your present board.</p>
        <p data-testid="hero-description">We will review your board, identify what needs to change, show you which board members can be reactivated, and tell you the exact type of board members you may need to recruit to complement your present board and strengthen your fundraising.</p>
        <p className="hero-note" data-testid="hero-response-time"><Check size={17} /> Choose the board problem you want to solve and build your starting point.</p>
      </div>
      <div className="hero-visual" aria-hidden="true">
        <div className="visual-grid" />
        <div className="mission-card"><span className="mission-label">MISSION</span><strong>Turn shared purpose into fundraising momentum.</strong><div className="people-row"><i /><i /><i /><i /><i /></div></div>
        <div className="impact-stat"><strong>3</strong><span>stages to a stronger board</span></div>
      </div>
    </section>

    <section id="how-it-works" className="section transformation" data-testid="transformation-section">
      <p className="eyebrow" data-testid="transformation-eyebrow">A practical path forward</p>
      <h2 data-testid="transformation-heading">We Help You Transform Your Board in Three Stages</h2>
      <div className="stage-grid">
        {stages.map(({ number, icon: Icon, title, text, button, path }, index) => <article className="stage-card" key={title} data-testid={`transformation-stage-${index + 1}`}><div className="stage-top"><span>{number}</span><Icon size={25} /></div><h3>{title}</h3><p>{text}</p><a className="button stage-cta" href={path} data-testid={`stage-offer-button-${index + 1}`}>{button} <ArrowRight size={16} /></a></article>)}
      </div>
    </section>

    <TestimonialsSection />

    <section id="what-we-fix" className="section discovery" data-testid="discovery-section">
      <div className="section-heading"><div><p className="eyebrow" data-testid="discovery-eyebrow">Clarity before action</p><h2 data-testid="discovery-heading">Discover Exactly What Your Board Needs</h2></div><p data-testid="discovery-intro">Your board should become one of the strongest forces moving your mission and fundraising forward.</p></div>
      <div className="discovery-grid">
        {discoveries.map(([title, text], index) => <article key={title} className="discovery-card" data-testid={`discovery-card-${index + 1}`}><span className="check-seal"><Check size={17} /></span><div><h3>{title}</h3><p>{text}</p></div></article>)}
      </div>
    </section>

    <section className="assessment-cta" data-testid="assessment-call-to-action">
      <div><p className="eyebrow light" data-testid="assessment-cta-eyebrow">Start with the truth about your board</p><h2 data-testid="assessment-cta-heading">Tell Us What Is Happening With Your Present Board</h2><p data-testid="assessment-cta-text">Complete the assessment below. We will review your answers and tell you what to do to transform your present board into a powerhouse fundraising board.</p></div>
      <OfferChoices location="middle" />
    </section>

    <FounderStorySection />

    <section className="final-cta" data-testid="final-call-to-action"><p className="eyebrow" data-testid="final-cta-eyebrow">A board built for impact</p><h2 data-testid="final-cta-heading">Build the Board Your Nonprofit Needs to Raise Money and Fulfil Its Mission</h2><p data-testid="final-cta-text">Tell us what is happening with your present board. We will review your answers and show you what needs to change, which board members can be reactivated, the exact people you need to recruit and how to activate the entire board around fundraising.</p><OfferChoices location="final" /></section>

    <section className="join-network-cta" data-testid="homepage-join-board-section"><div><p className="eyebrow light">Professional board service</p><h2>Are You a Professional Looking to Join a Nonprofit Board?</h2><p>Create your professional profile, tell us the causes you care about and receive board opportunities that match your skills, experience, location and availability.</p></div><button className="button button-light" onClick={onJoin} data-testid="homepage-join-network-button">Join the Board Applicant Network <ArrowRight size={18} /></button></section>

    <footer id="footer" className="footer" data-testid="site-footer"><a className="brand footer-brand" href="#top" data-testid="footer-brand-link"><img src={logoUrl} alt="Nonprofit Board Builder" data-testid="footer-brand-logo-image" /></a><p data-testid="footer-statement">Nonprofit Board Builder helps nonprofits reactivate, recruit and activate powerhouse fundraising boards.</p><div className="footer-links"><a href="#top" data-testid="footer-about-link">About</a><a href="#how-it-works" data-testid="footer-how-it-works-link">How It Works</a><a href="#footer" data-testid="footer-contact-link">Contact</a><a href="/privacy-policy" data-testid="footer-privacy-link">Privacy Policy</a><a href="/terms" data-testid="footer-terms-link">Terms</a></div></footer>
  </main>
);
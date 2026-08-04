import { ArrowRight, Check, RefreshCcw, Rocket, Users } from "lucide-react";

const logoUrl = "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/2qaqmobl_Minimalist%20nonprofit%20logo%20design.png";

const stages = [
  { number: "01", icon: RefreshCcw, title: "Reactivate Your Present Board", text: "Identify the board members who can be recommitted, re-engaged and given meaningful responsibilities based on their strengths, experience and relationships." },
  { number: "02", icon: Users, title: "Recruit the Board Members You Are Missing", text: "Identify and recruit people with the fundraising experience, professional skills and networks required to complement your present board." },
  { number: "03", icon: Rocket, title: "Activate Your Board to Start Raising Money", text: "Help present and new board members take responsibility for fundraising in their areas of strength while contributing to the strategy, team, materials and consistent execution required to raise money." },
];

const discoveries = [
  ["Which Present Board Members Can Be Reactivated", "Identify the people who still believe in the mission and can become active again with clear expectations, responsibility and support."],
  ["Which Board Members May Need to Step Down", "Recognize when inactive, disruptive or uncommitted board members are preventing the board from moving forward."],
  ["The Exact Board Members You Need to Recruit", "Identify the skills, experience, relationships and fundraising capacity missing from the present board."],
  ["How to Activate the Board Around Fundraising", "Give every board member a clear role based on what they know, who they know and what they can confidently help the organization execute."],
  ["What Fundraising System the Board Must Help Build", "Determine whether the organization needs a fundraising strategy, fundraising team, fundraising materials or stronger execution."],
  ["The Best Way to Transform the Board", "Determine whether the organization needs guidance, one-on-one support or complete help executing the board transformation."],
];

export const LandingPage = ({ onStart }) => (
  <main data-testid="landing-page">
    <nav className="site-nav" data-testid="site-navigation">
      <a className="brand" href="#top" data-testid="brand-logo-link"><img src={logoUrl} alt="Nonprofit Board Builder" data-testid="brand-logo-image" /></a>
      <div className="nav-links">
        <a href="#how-it-works" data-testid="how-it-works-link">How It Works</a>
        <a href="#what-we-fix" data-testid="what-we-fix-link">What We Help You Fix</a>
        <button onClick={onStart} className="nav-text-button" data-testid="tell-us-nav-link">Tell Us About Your Board</button>
      </div>
      <button onClick={onStart} className="button button-small" data-testid="nav-start-assessment-button">Tell Us About Your Present Board</button>
    </nav>

    <section id="top" className="hero" data-testid="hero-section">
      <div className="hero-copy">
        <p className="eyebrow" data-testid="hero-eyebrow">Your mission needs more than a board on paper</p>
        <h1 data-testid="hero-headline">Build the Powerhouse <em>Fundraising Board</em> Your Nonprofit Needs to Succeed</h1>
        <p className="hero-lead" data-testid="hero-supporting-text">Tell us about your present board.</p>
        <p data-testid="hero-description">We will review your board, identify what needs to change, show you which board members can be reactivated, and tell you the exact type of board members you may need to recruit to complement your present board and strengthen your fundraising.</p>
        <button onClick={onStart} className="button" data-testid="hero-start-assessment-button">Tell Us About Your Present Board <ArrowRight size={18} /></button>
        <p className="hero-note" data-testid="hero-response-time"><Check size={17} /> Complete the short board assessment and look out for our response within 24 hours.</p>
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
        {stages.map(({ number, icon: Icon, title, text }, index) => <article className="stage-card" key={title} data-testid={`transformation-stage-${index + 1}`}><div className="stage-top"><span>{number}</span><Icon size={25} /></div><h3>{title}</h3><p>{text}</p></article>)}
      </div>
    </section>

    <section id="what-we-fix" className="section discovery" data-testid="discovery-section">
      <div className="section-heading"><div><p className="eyebrow" data-testid="discovery-eyebrow">Clarity before action</p><h2 data-testid="discovery-heading">Discover Exactly What Your Board Needs</h2></div><p data-testid="discovery-intro">Your board should become one of the strongest forces moving your mission and fundraising forward.</p></div>
      <div className="discovery-grid">
        {discoveries.map(([title, text], index) => <article key={title} className="discovery-card" data-testid={`discovery-card-${index + 1}`}><span className="check-seal"><Check size={17} /></span><div><h3>{title}</h3><p>{text}</p></div></article>)}
      </div>
    </section>

    <section className="assessment-cta" data-testid="assessment-call-to-action">
      <div><p className="eyebrow light" data-testid="assessment-cta-eyebrow">Start with the truth about your board</p><h2 data-testid="assessment-cta-heading">Tell Us What Is Happening With Your Present Board</h2><p data-testid="assessment-cta-text">Complete the assessment below. We will review your answers and tell you what to do to transform your present board into a powerhouse fundraising board.</p></div>
      <button onClick={onStart} className="button button-light" data-testid="middle-start-assessment-button">Start My Board Assessment <ArrowRight size={18} /></button>
    </section>

    <section className="final-cta" data-testid="final-call-to-action"><p className="eyebrow" data-testid="final-cta-eyebrow">A board built for impact</p><h2 data-testid="final-cta-heading">Your Board Should Be Helping Your Nonprofit Raise Money and Fulfil Its Mission</h2><p data-testid="final-cta-text">Tell us what is happening with your present board and we will show you what needs to change.</p><button onClick={onStart} className="button" data-testid="final-start-assessment-button">Tell Us About Your Present Board <ArrowRight size={18} /></button></section>

    <footer id="footer" className="footer" data-testid="site-footer"><a className="brand footer-brand" href="#top" data-testid="footer-brand-link"><img src={logoUrl} alt="Nonprofit Board Builder" data-testid="footer-brand-logo-image" /></a><p data-testid="footer-statement">Nonprofit Board Builder helps nonprofits reactivate, recruit and activate powerhouse fundraising boards.</p><div className="footer-links"><a href="#top" data-testid="footer-about-link">About</a><a href="#how-it-works" data-testid="footer-how-it-works-link">How It Works</a><a href="#footer" data-testid="footer-contact-link">Contact</a><a href="#footer" data-testid="footer-privacy-link">Privacy Policy</a><a href="#footer" data-testid="footer-terms-link">Terms</a></div></footer>
  </main>
);
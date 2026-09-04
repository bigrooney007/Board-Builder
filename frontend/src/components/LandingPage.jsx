import { useState } from "react";
import axios from "axios";
import { ArrowRight } from "lucide-react";
import { TestimonialsSection } from "@/components/TestimonialsSection";
import { FounderStorySection } from "@/components/FounderStorySection";
import { BlogSlider } from "@/pages/BlogPages";
import { SITE_CONTENT, landingPageText } from "@/content/siteContent";

const logoUrl = "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/2qaqmobl_Minimalist%20nonprofit%20logo%20design.png";
const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const home = SITE_CONTENT.home;

const LeadMagnetForm = ({ location }) => {
  const [form, setForm] = useState({ name: "", email: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (!form.name.trim() || !form.email.trim()) { setError("Enter your name and email to get instant access."); return; }
    setBusy(true);
    try {
      const response = await axios.post(`${API}/funnel-leads/lead-magnet`, { ...form, origin_url: window.location.origin });
      try { sessionStorage.setItem("funnelLeadContext", JSON.stringify({ result_token: response.data.token })); } catch { /* best effort */ }
      window.location.href = response.data.redirect_url;
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your details. Please try again.");
      setBusy(false);
    }
  };
  return (
    <form className="lead-magnet-form" onSubmit={submit} data-testid={`${location}-lead-magnet-form`} style={{ marginTop: 22, display: "flex", flexDirection: "column", gap: 12, maxWidth: 460 }}>
      <p style={{ margin: 0 }}><strong>{home.leadFormPrompt}</strong></p>
      <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Name" aria-label="Name" data-testid={`${location}-lead-name-input`} style={{ padding: "12px 14px", borderRadius: 6, border: "1px solid #cfd6d2", fontSize: "1rem" }} />
      <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Email" aria-label="Email" data-testid={`${location}-lead-email-input`} style={{ padding: "12px 14px", borderRadius: 6, border: "1px solid #cfd6d2", fontSize: "1rem" }} />
      <button type="submit" className="button button-light" disabled={busy} data-testid={`${location}-lead-submit-button`}>
        {busy ? "One moment…" : home.leadFormCta} <ArrowRight size={16} />
      </button>
      {error && <p className="submit-error" data-testid={`${location}-lead-error`}>{error}</p>}
    </form>
  );
};

export const LandingPage = ({ onJoin }) => (
  <main data-testid="landing-page">
    <nav className="site-nav" data-testid="site-navigation">
      <a className="brand" href="#top" data-testid="brand-logo-link"><img src={logoUrl} alt={landingPageText.nonprofitBoardBuilder} data-testid="brand-logo-image" /></a>
      <div className="nav-links">
        <a href="#success-stories" data-testid="success-stories-link">{home.nav.successStories}</a>
        <a href="#my-story" data-testid="my-story-link">{home.nav.myStory}</a>
        <button onClick={onJoin} className="nav-text-button" data-testid="join-board-nav-link">{home.nav.joinABoard}</button>
      </div>
      <div className="nav-offer-buttons" data-testid="navigation-offer-choices"><a href="/login" data-testid="nav-login-link">{home.nav.logIn}</a></div>
    </nav>

    <section id="top" className="hero-banner" data-testid="hero-section">
      <div className="hero-banner-inner">
        <h1 data-testid="hero-headline">{home.heroTitle}</h1>
        <p className="hero-banner-lead" data-testid="hero-supporting-text"><strong>{home.heroSubtitle}</strong></p>
        <LeadMagnetForm location="hero" />
      </div>
    </section>

    <TestimonialsSection />

    <FounderStorySection />

    <section className="final-cta" data-testid="final-call-to-action">
      <p className="eyebrow" data-testid="final-cta-eyebrow">{home.finalCta.eyebrow}</p>
      <h2 data-testid="final-cta-heading">{home.heroSubtitle}</h2>
      <p style={{ marginTop: 16 }}><a className="button" href="#top" data-testid="final-cta-lead-button">{home.leadFormCta}</a></p>
    </section>

    <BlogSlider />

    <section className="join-network-cta" data-testid="homepage-join-board-section"><div><p className="eyebrow light">{home.joinNetwork.eyebrow}</p><h2>{home.joinNetwork.heading}</h2><p>{home.joinNetwork.text}</p></div><button className="button button-light" onClick={onJoin} data-testid="homepage-join-network-button">{home.joinNetwork.button} <ArrowRight size={18} /></button></section>

    <footer id="footer" className="footer" data-testid="site-footer"><a className="brand footer-brand" href="#top" data-testid="footer-brand-link"><img src={logoUrl} alt={landingPageText.nonprofitBoardBuilder2} data-testid="footer-brand-logo-image" /></a><p data-testid="footer-statement">{home.footer.statement}</p><div className="footer-links"><a href="#top" data-testid="footer-about-link">{home.footer.about}</a><a href="#footer" data-testid="footer-contact-link">{home.footer.contact}</a><a href="/privacy-policy" data-testid="footer-privacy-link">{home.footer.privacy}</a><a href="/terms" data-testid="footer-terms-link">{home.footer.terms}</a></div></footer>
  </main>
);

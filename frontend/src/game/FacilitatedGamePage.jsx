import { useEffect, useState } from "react";
import axios from "axios";
import { BfgShell } from "./gameShared";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const sectionStyle = { maxWidth: 820, margin: "0 auto", padding: "clamp(44px, 6vw, 76px) clamp(20px, 5vw, 40px)", borderTop: "1px solid #E5E7EB" };
const h2Style = { fontSize: "clamp(24px, 3.4vw, 34px)", lineHeight: 1.15, marginBottom: 22 };
const h3Style = { fontSize: "clamp(17px, 2.2vw, 21px)", marginTop: 30, marginBottom: 10 };
const pStyle = { marginTop: 14, fontSize: 16 };
const listStyle = { marginTop: 14, paddingLeft: 22, color: "#4B5563", lineHeight: 1.75, fontSize: 16 };

export default function FacilitatedGamePage() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { document.title = "Facilitated Board Fundraising Game"; }, []);

  const buy = async () => {
    setBusy(true); setError("");
    try {
      const response = await axios.post(`${API}/payments/facilitated-game-checkout`, {
        origin_url: window.location.origin, cancel_path: "/organize-board-fundraising-game",
      });
      window.location.href = response.data.checkout_url;
    } catch {
      setError("We could not open checkout. Please try again.");
      setBusy(false);
    }
  };

  const Cta = ({ label, testId, supporting }) => (
    <div style={{ marginTop: 28 }}>
      <button className="bfg-btn bfg-btn-primary" style={{ fontSize: 16, padding: "16px 32px" }} disabled={busy}
        onClick={buy} data-testid={testId}>
        {busy ? "Opening Checkout…" : label}
      </button>
      {supporting && <p style={{ marginTop: 12, fontSize: 14 }}>{supporting}</p>}
      {error && <p className="bfg-error" style={{ marginTop: 12, maxWidth: 480 }} data-testid={`${testId}-error`}>{error}</p>}
    </div>
  );

  return (
    <BfgShell>
      <main data-testid="bfg-facilitated-page">
        {/* SECTION 1 — HERO */}
        <section className="bfg-hero" data-testid="facilitated-hero">
          <div className="bfg-hero-inner" style={{ textAlign: "left", maxWidth: 860 }}>
            <span className="bfg-badge">FACILITATED BOARD FUNDRAISING GAME</span>
            <h1>Let Us Organize And Facilitate The Board Fundraising Game For Your Organization</h1>
            <p style={{ ...pStyle, marginTop: 22, fontSize: "clamp(15px, 2vw, 18px)", color: "#374151" }}>Bring your board together to build your organization's fundraising strategy, identify how every board member can participate and leave the process knowing exactly how your organization plans to raise money.</p>
            <p style={pStyle}>You don't have to organize and facilitate the entire process yourself.</p>
            <p style={pStyle}>We will work with you to prepare your organization, get your board involved, guide everyone through the Board Fundraising Game and facilitate your Board Fundraising Day/Night with you.</p>
            <p style={{ marginTop: 26, fontFamily: "Outfit", fontWeight: 800, fontSize: "clamp(28px, 4vw, 40px)", color: "#111827" }} data-testid="facilitated-hero-price">$3,497 ONE-TIME</p>
            <Cta label="ORGANIZE MY BOARD FUNDRAISING GAME — $3,497" testId="facilitated-cta-hero"
              supporting="After payment, you will complete our Fundraising Activation Intake and book your first meeting with Rooney Akpesiri." />
          </div>
        </section>

        {/* SECTION 2 */}
        <section style={sectionStyle} data-testid="facilitated-section-2">
          <h2 style={h2Style}>Your Board Should Help Ensure Your Organization Is Adequately Funded</h2>
          <p style={pStyle}>Funding should not rest entirely on the founder or Executive Director.</p>
          <p style={pStyle}>One of the board's most important responsibilities is helping ensure the organization is adequately funded.</p>
          <p style={pStyle}>But getting board members involved in fundraising is difficult when they don't understand the organization's fundraising strategy, were not part of building it and don't know exactly how they are expected to participate.</p>
          <p style={pStyle}>That's why we created the Board Fundraising Game.</p>
          <p style={pStyle}>Instead of handing your board a fundraising plan and asking them to execute it, we bring them into the process of building the strategy with you.</p>
          <p style={pStyle}>Because people who plan together execute together.</p>
        </section>

        {/* SECTION 3 */}
        <section style={sectionStyle} data-testid="facilitated-section-3">
          <h2 style={h2Style}>What We Will Help Your Board Build</h2>
          <p style={pStyle}>To raise money exponentially, your organization needs a fundraising strategy you and everyone in your organization can commit to.</p>
          <p style={pStyle}>A fundraising strategy that clearly spells out:</p>
          <ul style={listStyle}>
            <li>The exact type of people with the strongest reason to fund your mission.</li>
            <li>The exact type of businesses with the strongest reason to fund your mission.</li>
            <li>The exact type of grantors with the strongest reason to fund your mission.</li>
            <li>Where to consistently find them.</li>
            <li>How to attract them.</li>
            <li>The exact process to raise money from individuals.</li>
            <li>The exact process to raise money from businesses.</li>
            <li>The exact process to raise money from grantors.</li>
            <li>The people, technology, materials, resources and content needed to execute the strategy.</li>
            <li>And how your board members want to participate.</li>
          </ul>
          <p style={pStyle}>Then we bring everybody together to review the strategy, identify priorities and agree on its execution.</p>
        </section>

        {/* SECTION 4 */}
        <section style={sectionStyle} data-testid="facilitated-section-4">
          <h2 style={h2Style}>Here's How We Will Work With You</h2>
          <h3 style={h3Style}>1. Understand Your Organization And Fundraising Goal</h3>
          <p style={pStyle}>We start by understanding your organization, your board, your fundraising goal, your present fundraising situation and what is already working.</p>
          <p style={pStyle}>We want to understand the individual donors, businesses and grantors already supporting your organization, how you currently raise money from them, who is presently helping with fundraising and the technology, materials and resources you already have.</p>
          <h3 style={h3Style}>2. Prepare Your Board Fundraising Game</h3>
          <p style={pStyle}>We prepare the process around your organization and fundraising goal.</p>
          <p style={pStyle}>The game helps everybody think about the same fundraising challenge and contribute ideas that can strengthen the strategy.</p>
          <h3 style={h3Style}>3. Get Your Board And Everyone In Your Organization Involved</h3>
          <p style={pStyle}>Your board members and other people within your organization play the game individually before the meeting.</p>
          <p style={pStyle}>Each person learns how fundraising works while contributing their own ideas about:</p>
          <ul style={listStyle}>
            <li>Who should fund your mission.</li>
            <li>Where to find them.</li>
            <li>How to attract them.</li>
            <li>How your organization should raise money from them.</li>
            <li>And how they personally believe they can participate.</li>
          </ul>
          <p style={pStyle}>The more people that play the game, the richer your fundraising strategy becomes and the more people you have to help execute it with you.</p>
          <h3 style={h3Style}>4. Build Your Working Fundraising Strategy</h3>
          <p style={pStyle}>We bring the information and ideas together into your Working Fundraising Strategy.</p>
          <p style={pStyle}>The strategy shows how your organization can raise money from individuals, businesses and grantors and what needs to be built to execute the strategy consistently.</p>
          <h3 style={h3Style}>5. Facilitate Your Board Fundraising Day/Night</h3>
          <p style={pStyle}>We facilitate the Board Fundraising Day/Night with your organization.</p>
          <p style={pStyle}>Your board reviews the ideas contributed by everyone, identifies the strongest fundraising priorities, reviews additional recommendations and strengthens the strategy together.</p>
          <p style={pStyle}>Then your board agrees on how the strategy should be executed.</p>
          <h3 style={h3Style}>6. Complete Your Final Board Fundraising Strategy</h3>
          <p style={pStyle}>The priorities, decisions, responsibilities and additional ideas agreed during your board meeting are brought together into your Final Board Fundraising Strategy.</p>
          <p style={pStyle}>You leave with a clear working document showing how your organization plans to raise money.</p>
          <h3 style={h3Style}>7. Move Into Execution</h3>
          <p style={pStyle}>Every participating board member can see exactly how they agreed to participate.</p>
          <p style={pStyle}>They receive their personal Board Fundraising Portfolio.</p>
          <p style={pStyle}>They receive the execution materials they need for the responsibilities they selected.</p>
          <p style={pStyle}>And they receive Relationship Mapping so they can begin identifying people, businesses and grantors within their own networks who match the ideal funder profiles identified in your strategy.</p>
        </section>

        {/* SECTION 5 */}
        <section style={sectionStyle} data-testid="facilitated-section-5">
          <h2 style={h2Style}>What Your Organization Will Leave With</h2>
          <ul style={listStyle}>
            <li>A clear fundraising strategy showing exactly who your organization should raise money from, where to find them, how to attract them and how to raise money from them.</li>
            <li>A complete fundraising process for individuals.</li>
            <li>A complete fundraising process for businesses.</li>
            <li>A complete fundraising process for grantors.</li>
            <li>A board that understands how your organization plans to raise money.</li>
            <li>Fundraising priorities agreed by your board.</li>
            <li>A clear understanding of the people, technology, materials, resources and content needed to execute the strategy.</li>
            <li>Clear board-member participation based on how each person genuinely wants to help.</li>
            <li>Individual Board Fundraising Portfolios.</li>
            <li>Personalized Execution Materials.</li>
            <li>Relationship Mapping so board members can identify potential funders already inside their personal, professional, business and community networks.</li>
            <li>And a stronger foundation for building and maintaining the fundraising system that runs your strategy consistently.</li>
          </ul>
        </section>

        {/* SECTION 6 */}
        <section style={sectionStyle} data-testid="facilitated-section-6">
          <h2 style={h2Style}>You Don't Have To Run The Process Alone</h2>
          <p style={pStyle}>The $497 Board Fundraising Game gives you the complete platform to organize and run the process yourself.</p>
          <p style={pStyle}>The $3,497 Facilitated Board Fundraising Game is for organizations that want us to work through the process with them.</p>
          <p style={pStyle}>We help prepare the process.</p>
          <p style={pStyle}>We help get your board involved.</p>
          <p style={pStyle}>We guide everyone through the game.</p>
          <p style={pStyle}>We help bring everyone's ideas together.</p>
          <p style={pStyle}>And we facilitate your Board Fundraising Day/Night with you.</p>
          <p style={pStyle}>So instead of trying to figure out how to bring everybody together around fundraising, you have a clear process and somebody experienced guiding it with you.</p>
        </section>

        {/* SECTION 7 */}
        <section style={sectionStyle} data-testid="facilitated-section-7">
          <h2 style={h2Style}>People Who Plan Together Execute Together</h2>
          <p style={pStyle}>One of the biggest mistakes organizations make is building a fundraising plan and then taking it to the board and expecting everybody to execute it.</p>
          <p style={pStyle}>We take a different approach.</p>
          <p style={pStyle}>Your board helps build the strategy.</p>
          <p style={pStyle}>They contribute their ideas.</p>
          <p style={pStyle}>They understand how the strategy works.</p>
          <p style={pStyle}>They tell you how they want to participate.</p>
          <p style={pStyle}>Then everybody comes together to decide what the organization should actually execute.</p>
          <p style={pStyle}>When you build this strategy with your board and everyone in your organization, they can help execute the strategy by raising money individually and working with you to build and maintain the fundraising system that runs the strategy consistently.</p>
          <p style={pStyle}>That's the opportunity the Board Fundraising Game gives your organization.</p>
        </section>

        {/* SECTION 8 — PRICING */}
        <section style={sectionStyle} data-testid="facilitated-section-pricing">
          <h2 style={h2Style}>Let Us Organize The Board Fundraising Game For Your Organization</h2>
          <div style={{ border: "1px solid #E5E7EB", borderRadius: 20, background: "#ffffff", padding: "clamp(26px, 4vw, 44px)", boxShadow: "0 18px 48px rgba(17, 24, 39, 0.08)" }}>
            <p style={{ fontFamily: "Outfit", fontWeight: 800, fontSize: "clamp(34px, 5vw, 48px)", color: "#111827", margin: 0 }} data-testid="facilitated-pricing-amount">$3,497</p>
            <p style={{ marginTop: 6, fontWeight: 700, letterSpacing: "0.12em", fontSize: 13, color: "#4f46e5" }}>ONE-TIME ENGAGEMENT</p>
            <p style={{ ...pStyle, fontWeight: 600, color: "#111827" }}>Includes:</p>
            <ul style={listStyle}>
              <li>Complete Board Fundraising Game access for your organization</li>
              <li>Board preparation and guidance</li>
              <li>Individual Board Fundraising Games</li>
              <li>Participation from other people within your organization</li>
              <li>Working Fundraising Strategy</li>
              <li>Board Fundraising Day/Night facilitation</li>
              <li>Board Strategy Review</li>
              <li>Final Board Fundraising Strategy</li>
              <li>Board Fundraising Portfolios</li>
              <li>Personalized Execution Materials</li>
              <li>Relationship Mapping</li>
            </ul>
            <Cta label="ORGANIZE MY BOARD FUNDRAISING GAME — $3,497" testId="facilitated-cta-pricing"
              supporting="After payment, complete your Fundraising Activation Intake and book your first meeting with Rooney Akpesiri." />
          </div>
        </section>

        {/* SECTION 9 — FINAL CTA */}
        <section style={{ ...sectionStyle, paddingBottom: "clamp(70px, 9vw, 120px)" }} data-testid="facilitated-section-final">
          <h2 style={h2Style}>Ready To Build Your Fundraising Strategy With Your Board?</h2>
          <p style={pStyle}>You don't have to continue carrying fundraising alone.</p>
          <p style={pStyle}>Bring your board into the process.</p>
          <p style={pStyle}>Let us work with you to build the strategy, facilitate the conversation and create a clear pathway for everyone to begin participating.</p>
          <p style={pStyle}>You can leave your next board meeting with your fundraising strategy plan and your board eager and ready to start raising money and building your organization's fundraising system.</p>
          <Cta label="YES, ORGANIZE THE GAME FOR US — $3,497" testId="facilitated-cta-final" />
        </section>
      </main>
    </BfgShell>
  );
}

import { useState } from "react";
import axios from "axios";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function FundraisingBoardBuilderOfferPage() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const startCheckout = async () => {
    setBusy(true);
    setError("");
    try {
      let resultToken = "";
      try { resultToken = JSON.parse(sessionStorage.getItem("funnelLeadContext") || "{}").result_token || ""; } catch { /* best effort */ }
      const response = await axios.post(`${API}/payments/fundraising-board-builder-checkout`, {
        origin_url: window.location.origin, result_token: resultToken, cancel_path: "/offer/fundraising-board-builder",
      });
      window.location.href = response.data.checkout_url;
    } catch {
      setError("We could not start the checkout. Please try again.");
      setBusy(false);
    }
  };

  const Cta = ({ id }) => (
    <div style={{ textAlign: "center", margin: "28px 0" }}>
      <button type="button" className="button" onClick={startCheckout} disabled={busy}
        data-testid={`fbb-get-started-${id}`} style={{ fontSize: "1.1rem", padding: "16px 38px", justifyContent: "center" }}>
        {busy ? "Starting checkout…" : "GET STARTED NOW"}
      </button>
      {error && <p className="submit-error" data-testid={`fbb-checkout-error-${id}`} style={{ marginTop: 10 }}>{error}</p>}
    </div>
  );

  const H2 = ({ children, id }) => (
    <h2 data-testid={`fbb-heading-${id}`} style={{ textAlign: "center", fontWeight: 800, fontSize: "1.6rem", marginTop: 52, letterSpacing: "0.02em" }}>{children}</h2>
  );

  return (
    <FunnelLayout restrained>
      <main className="offer-sales-page" data-testid="fbb-offer-page">
        <header className="funnel-hero-banner offer-sales-banner" data-testid="fbb-offer-hero">
          <h1 data-testid="fbb-offer-headline">BUILD THE FUNDRAISING BOARD YOUR ORGANIZATION NEEDS</h1>
          <p className="offer-sales-lead" data-testid="fbb-offer-subtitle"><strong>Build the board that can help you raise money consistently and work with you to build the fundraising system your organization needs to remain financially sustainable.</strong></p>
          <i aria-hidden="true" />
        </header>
        <div className="offer-sales-container">
          <article className="offer-sales-body" data-testid="fbb-offer-body">
            <p style={{ textAlign: "center", fontWeight: 800, fontSize: "1.25rem", marginTop: 26 }} data-testid="fbb-discount-banner-top">50% OFF FOR THE NEXT 7 DAYS</p>
            <p style={{ textAlign: "center", margin: "6px 0 0" }} data-testid="fbb-price-line">Regular price <s>$997</s> — today <strong>$497</strong></p>
            <Cta id="hero" />

            <H2 id="what-you-get">SEE WHAT YOU GET</H2>
            <p>You don't need another consultant to come in and take over your board.</p>
            <p>You need the right process, tools and materials to lead your board yourself.</p>
            <p>Once you get started, you will receive access to two complete systems:</p>

            <section className="member-card" data-testid="fbb-activation-block" style={{ marginTop: 22 }}>
              <h3 style={{ fontWeight: 800 }}>BOARD FUNDRAISING ACTIVATION</h3>
              <p>You will activate your present board members to start raising money and working with you to build your organization's fundraising system.</p>
              <ul>
                <li>Create your organization's fundraising strategy, establishing your organization's fundraising direction.</li>
                <li>You will work with your board members to build your organization's fundraising strategy.</li>
                <li>Equip each board member to start raising money for your organization.</li>
                <li>Activate and engage your board members to start stepping up to their responsibilities of ensuring your organization is adequately funded.</li>
              </ul>
              <p>Everything is already laid out for you.</p>
              <p>You lead your board.</p>
              <p>We give you the process and everything you need to execute it.</p>
            </section>
            <Cta id="activation" />

            <section className="member-card" data-testid="fbb-recruitment-block">
              <h3 style={{ fontWeight: 800 }}>BOARD RECRUITMENT</h3>
              <p>Recruit the professional board members your organization needs, including people with fundraising experience who can strengthen your ability to raise money.</p>
              <p>You will be able to:</p>
              <ul>
                <li>Identify the board members your organization needs to recruit.</li>
                <li>Launch your board recruitment campaign the right way.</li>
                <li>Get access to everything you need to select the right board members.</li>
                <li>Run your reference checks and background checks.</li>
                <li>Onboard your new board members like a pro so they get on the ground running.</li>
                <li>Equip each board member with their own individual Board Member Portfolio so everyone knows how they contribute to the board.</li>
              </ul>
            </section>
            <p>You decide which system you need first.</p>
            <p>If you already have board members, you may decide to start by activating them.</p>
            <p>If you need new board members or fundraising experience on your board, you may decide to start with recruitment.</p>
            <p>If you need both, you have access to both.</p>
            <Cta id="systems" />

            <H2 id="process">SEE THE PROCESS</H2>
            <section data-testid="fbb-process-steps">
              <h3 style={{ fontWeight: 800 }}>STEP 1: GET STARTED</h3>
              <p>Make your payment and complete your organization intake form.</p>
              <p>This gives us the information needed to personalize the tools, documents and materials you will use throughout the process.</p>
              <h3 style={{ fontWeight: 800 }}>STEP 2: CHOOSE WHERE YOU WANT TO START</h3>
              <p>Inside your account, you will see two sections:</p>
              <p><strong>Board Fundraising Activation</strong> and <strong>Board Recruitment</strong></p>
              <p>You can move between both sections whenever you want.</p>
              <p>There is no complicated course to complete.</p>
              <p>There are no unnecessary modules.</p>
              <p>Simply choose the process you want to execute and follow the steps on the page.</p>
              <h3 style={{ fontWeight: 800 }}>STEP 3: USE THE TOOLS</h3>
              <p>At each stage, I will explain what you are doing and why.</p>
              <p>Then you will receive the exact form, email, script, guide, document or resource you need to take the next step.</p>
              <p>You use it.</p>
              <p>Your board responds.</p>
              <p>You bring the information back into the system.</p>
              <p>Then you move forward.</p>
              <h3 style={{ fontWeight: 800 }}>STEP 4: BUILD YOUR FUNDRAISING BOARD</h3>
              <p>The goal is simple.</p>
              <p>Get your present board members participating in fundraising.</p>
              <p>Bring the right professional board members into your organization where needed.</p>
              <p>Work with your board to build a fundraising strategy.</p>
              <p>Build the system that can execute that strategy consistently.</p>
              <p>And stop carrying the responsibility of funding your organization alone.</p>
            </section>
            <Cta id="process" />

            <H2 id="guarantee">OUR GUARANTEE</H2>
            <section data-testid="fbb-guarantee">
              <p style={{ textAlign: "center", fontWeight: 800 }}>USE THE SYSTEM. TAKE THE ACTION. IF IT ISN'T FOR YOU, LET US KNOW.</p>
              <p>Go through the platform.</p>
              <p>Watch the instructions.</p>
              <p>Use the tools.</p>
              <p>Begin the process inside your organization.</p>
              <p>If you decide the system is not right for you within the next 24 hours, we will provide you a full refund.</p>
              <p>We want you buying this because you are ready to take action.</p>
            </section>
            <Cta id="guarantee" />

            <H2 id="testimonials">WHAT OTHER NONPROFIT LEADERS HAVE EXPERIENCED</H2>
          </article>
          <div className="offer-sales-testimonials" data-testid="fbb-testimonials">
            <TestimonialCarousel idPrefix="fbb-offer" />
          </div>
          <article className="offer-sales-body">
            <Cta id="after-testimonials" />

            <H2 id="fomo">50% OFF FOR THE NEXT 7 DAYS</H2>
            <section data-testid="fbb-fomo">
              <p>You already know whether your board is giving your organization the support it needs.</p>
              <p>You already know whether fundraising continues to fall heavily on you.</p>
              <p>And you already know whether you need additional people around you with the experience, relationships and expertise your organization needs.</p>
              <p>You can continue trying to figure the process out yourself.</p>
              <p>Or you can use a process that has already been laid out for you.</p>
              <p>For the next 7 days, you can get access to the complete Fundraising Board Builder system at 50% off.</p>
              <p>You receive both:</p>
              <p><strong>Board Fundraising Activation</strong> and <strong>Board Recruitment</strong></p>
              <p>One system.</p>
              <p>One account.</p>
              <p>Everything you need to start building the fundraising board your organization needs.</p>
            </section>
            <Cta id="final" />
          </article>
        </div>
      </main>
    </FunnelLayout>
  );
}

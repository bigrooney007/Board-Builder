import { useEffect, useState } from "react";
import axios from "axios";
import { BfgShell } from "./gameShared";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const steps = [
  ["1", "We Prepare The Game", "We learn your fundraising goal, current reality and board, then prepare the experience around your organization."],
  ["2", "Your Board Plays", "Board members contribute their own ideas before the meeting so the strategy is built with them, not handed to them."],
  ["3", "We Build The Working Strategy", "We bring everyone's ideas together into one practical fundraising strategy for individuals, businesses and grantors."],
  ["4", "We Facilitate Your Board Fundraising Day/Night", "We guide the conversation, help the board make decisions and agree on fundraising priorities and participation."],
  ["5", "You Leave Ready To Execute", "You receive the final strategy, board portfolios, execution materials and relationship mapping to help everyone start."],
];
const outcomes = [
  "Your Final Board Fundraising Strategy",
  "A board that understands and helped build the strategy",
  "Clear fundraising priorities and board participation",
  "Individual Board Fundraising Portfolios",
  "Personalized Execution Materials",
  "Relationship Mapping for potential funders in each board member's network",
];

export default function FacilitatedGamePage() {
  const [busy,setBusy]=useState(false); const [error,setError]=useState("");
  useEffect(()=>{document.title="Facilitated Board Fundraising Game";},[]);
  const buy=async()=>{setBusy(true);setError("");try{const r=await axios.post(`${API}/payments/facilitated-game-checkout`,{origin_url:window.location.origin,cancel_path:"/organize-board-fundraising-game"});window.location.href=r.data.checkout_url;}catch{setError("We could not open checkout. Please try again.");setBusy(false);}};
  const Cta=({id,label="ORGANIZE MY BOARD FUNDRAISING GAME — $3,497"})=><>
    <button className="bfg-btn bfg-btn-primary facilitated-cta" disabled={busy} onClick={buy} data-testid={id}>{busy?"Opening Secure Checkout…":label}</button>
    {error&&<p className="bfg-error" style={{marginTop:12}}>{error}</p>}
  </>;

  return <BfgShell><main className="facilitated-page" data-testid="bfg-facilitated-page">
    <section className="facilitated-hero">
      <span className="bfg-badge">FACILITATED BOARD FUNDRAISING GAME</span>
      <h1>Bring Your Board Together. Build The Fundraising Strategy Together. Leave Ready To Raise Money Together.</h1>
      <p>We organize and facilitate the Board Fundraising Game for your organization so you do not have to figure out how to get everyone involved yourself.</p>
      <div className="facilitated-price-card">
        <p className="facilitated-price">$3,497</p><p className="facilitated-kicker">ONE-TIME ENGAGEMENT</p>
        <Cta id="facilitated-cta-hero"/>
        <small>After payment, complete your intake and book your first meeting with Rooney Akpesiri.</small>
      </div>
    </section>

    <section className="facilitated-band">
      <h2>Your Board Should Help Build The Fundraising Strategy They Are Expected To Execute.</h2>
      <p>Fundraising becomes difficult when the strategy sits with one person and the board is simply asked to help. We bring your board into the process from the beginning.</p>
      <strong>People who plan together execute together.</strong>
    </section>

    <section className="facilitated-section">
      <p className="facilitated-eyebrow">HERE'S HOW IT WORKS</p>
      <h2>We Organize The Process. Your Board Builds It With Us.</h2>
      <div className="facilitated-steps">
        {steps.map(([n,title,text])=><article className="facilitated-card" key={n}><span>{n}</span><h3>{title}</h3><p>{text}</p></article>)}
      </div>
    </section>

    <section className="facilitated-section facilitated-soft">
      <p className="facilitated-eyebrow">WHAT YOU WILL BUILD</p>
      <h2>A Fundraising Strategy Your Board Understands And Can Help Execute.</h2>
      <p>Your board will help identify who should fund your mission, where to find them, how to attract them, how your organization should raise money from them and how each person wants to participate.</p>
      <div className="facilitated-three">
        <article className="facilitated-card"><h3>WHO</h3><p>The individuals, businesses and grantors with the strongest reason to fund your mission.</p></article>
        <article className="facilitated-card"><h3>HOW</h3><p>Where to find them, how to attract them and the practical process for raising money from them.</p></article>
        <article className="facilitated-card"><h3>WHO DOES WHAT</h3><p>How your board wants to participate and what is needed to execute the strategy consistently.</p></article>
      </div>
    </section>

    <section className="facilitated-section">
      <p className="facilitated-eyebrow">WHAT YOU LEAVE WITH</p>
      <h2>Not Another Plan Sitting In A Folder.</h2>
      <div className="facilitated-outcomes">{outcomes.map(x=><div className="facilitated-outcome" key={x}>✓ {x}</div>)}</div>
    </section>

    <section className="facilitated-section">
      <div className="facilitated-offer">
        <p className="facilitated-eyebrow">LET US RUN IT WITH YOU</p>
        <h2>Let Us Organize Your Board Fundraising Game.</h2>
        <p>We prepare the process, guide your board through the game, facilitate your Board Fundraising Day/Night and turn the decisions into the final strategy and execution materials.</p>
        <p className="facilitated-price">$3,497</p><p className="facilitated-kicker">ONE-TIME ENGAGEMENT</p>
        <Cta id="facilitated-cta-pricing"/>
        <small>Complete Board Fundraising Game access and facilitation for your organization.</small>
      </div>
    </section>

    <section className="facilitated-final">
      <h2>Stop Carrying Fundraising Alone.</h2>
      <p>Bring your board into the process and leave your next Board Fundraising Day/Night with a strategy everyone helped build and clear ways for each person to participate.</p>
      <Cta id="facilitated-cta-final" label="YES, ORGANIZE THE GAME FOR US — $3,497"/>
    </section>
  </main></BfgShell>;
}

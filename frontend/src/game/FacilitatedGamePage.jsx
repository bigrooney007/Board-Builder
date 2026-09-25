import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { BfgShell } from "./gameShared";
import { useHomepageContent } from "@/clean/platform";

export const FACILITATED_GAME_HOME_DEFAULTS = {
  badge: "FACILITATED BOARD FUNDRAISING GAME",
  headline: "Bring Your Board Together. Build The Fundraising Strategy Together. Leave Ready To Raise Money Together.",
  heroText: "We organize and facilitate the Board Fundraising Game for your organization so you do not have to figure out how to get everyone involved yourself.",
  price: "$3,497",
  priceKicker: "ONE-TIME ENGAGEMENT",
  applicationNote: "Apply first. We will review your application and follow up through email.",
  principleHeading: "Your Board Should Help Build The Fundraising Strategy They Are Expected To Execute.",
  principleText: "Fundraising becomes difficult when the strategy sits with one person and the board is simply asked to help. We bring your board into the process from the beginning.",
  principleStrong: "People who plan together execute together.",
  processEyebrow: "HERE'S HOW IT WORKS",
  processHeading: "We Organize The Process. Your Board Builds It With Us.",
  steps: [
    ["1", "We Prepare The Game", "We learn your fundraising goal, current reality and board, then prepare the experience around your organization."],
    ["2", "Your Board Plays", "Board members contribute their own ideas before the meeting so the strategy is built with them, not handed to them."],
    ["3", "We Build The Working Strategy", "We bring everyone's ideas together into one practical fundraising strategy for individuals, businesses and grantors."],
    ["4", "We Facilitate Your Board Fundraising Day/Night", "We guide the conversation, help the board make decisions and agree on fundraising priorities and participation."],
    ["5", "You Leave Ready To Execute", "You receive the final strategy, board portfolios, execution materials and relationship mapping to help everyone start."],
  ],
  buildEyebrow: "WHAT YOU WILL BUILD",
  buildHeading: "A Fundraising Strategy Your Board Understands And Can Help Execute.",
  buildText: "Your board will help identify who should fund your mission, where to find them, how to attract them, how your organization should raise money from them and how each person wants to participate.",
  buildCards: [
    ["WHO", "The individuals, businesses and grantors with the strongest reason to fund your mission."],
    ["HOW", "Where to find them, how to attract them and the practical process for raising money from them."],
    ["WHO DOES WHAT", "How your board wants to participate and what is needed to execute the strategy consistently."],
  ],
  outcomesEyebrow: "WHAT YOU LEAVE WITH",
  outcomesHeading: "Not Another Plan Sitting In A Folder.",
  outcomes: [
    "Your Final Board Fundraising Strategy",
    "A board that understands and helped build the strategy",
    "Clear fundraising priorities and board participation",
    "Individual Board Fundraising Portfolios",
    "Personal Executive Assistants With On-Demand Materials",
    "Relationship Mapping for potential funders in each board member's network",
  ],
  offerEyebrow: "LET US RUN IT WITH YOU",
  offerHeading: "Let Us Organize Your Board Fundraising Game.",
  offerText: "We prepare the process, guide your board through the game, facilitate your Board Fundraising Day/Night and turn the decisions into the final strategy and execution materials.",
  offerNote: "Apply to see if the facilitated Board Fundraising Game is the right fit for your organization.",
  finalHeading: "Stop Carrying Fundraising Alone.",
  finalText: "Bring your board into the process and leave your next Board Fundraising Day/Night with a strategy everyone helped build and clear ways for each person to participate.",
};

export default function FacilitatedGamePage() {
  const navigate=useNavigate();
  const copy=useHomepageContent("facilitated-game", FACILITATED_GAME_HOME_DEFAULTS);
  useEffect(()=>{document.title="Facilitated Board Fundraising Game";},[]);
  const Cta=({id,label="APPLY TO ORGANIZE YOUR BOARD FUNDRAISING GAME"})=><button className="bfg-btn bfg-btn-primary facilitated-cta" onClick={()=>navigate("/organize-board-fundraising-game/apply")} data-testid={id}>{label}</button>;

  return <BfgShell><main className="facilitated-page" data-testid="bfg-facilitated-page">
    <section className="facilitated-hero">
      <span className="bfg-badge">{copy.badge}</span>
      <h1>{copy.headline}</h1>
      <p>{copy.heroText}</p>
      <div className="facilitated-price-card">
        <p className="facilitated-price">{copy.price}</p><p className="facilitated-kicker">{copy.priceKicker}</p>
        <Cta id="facilitated-cta-hero"/>
        <small>{copy.applicationNote}</small>
      </div>
    </section>

    <section className="facilitated-band">
      <h2>{copy.principleHeading}</h2><p>{copy.principleText}</p><strong>{copy.principleStrong}</strong>
    </section>

    <section className="facilitated-section">
      <p className="facilitated-eyebrow">{copy.processEyebrow}</p><h2>{copy.processHeading}</h2>
      <div className="facilitated-steps">{(copy.steps||[]).map(([n,title,text])=><article className="facilitated-card" key={n}><span>{n}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
    </section>

    <section className="facilitated-section facilitated-soft">
      <p className="facilitated-eyebrow">{copy.buildEyebrow}</p><h2>{copy.buildHeading}</h2><p>{copy.buildText}</p>
      <div className="facilitated-three">{(copy.buildCards||[]).map(([title,text])=><article className="facilitated-card" key={title}><h3>{title}</h3><p>{text}</p></article>)}</div>
    </section>

    <section className="facilitated-section">
      <p className="facilitated-eyebrow">{copy.outcomesEyebrow}</p><h2>{copy.outcomesHeading}</h2>
      <div className="facilitated-outcomes">{(copy.outcomes||[]).map(x=><div className="facilitated-outcome" key={x}>✓ {x}</div>)}</div>
    </section>

    <section className="facilitated-section"><div className="facilitated-offer">
      <p className="facilitated-eyebrow">{copy.offerEyebrow}</p><h2>{copy.offerHeading}</h2><p>{copy.offerText}</p>
      <p className="facilitated-price">{copy.price}</p><p className="facilitated-kicker">{copy.priceKicker}</p>
      <Cta id="facilitated-cta-pricing"/><small>{copy.offerNote}</small>
    </div></section>

    <section className="facilitated-final">
      <h2>{copy.finalHeading}</h2><p>{copy.finalText}</p>
      <Cta id="facilitated-cta-final" label="YES, I WANT YOU TO ORGANIZE OUR GAME — APPLY NOW"/>
    </section>
  </main></BfgShell>;
}

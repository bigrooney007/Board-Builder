import {publicText} from '@/content/publicPresentation';
import { CheckCircle2 } from "lucide-react";
import "./demo-offers.css";

export default function DemoOfferCards({ product, selfGuided, supported, intro, busy, disabled = false, onBuy, error, offerEyebrow, offerHeading }) {
  const cards = [
    { key: "self-guided", label: "SELF-GUIDED PATHWAY", price: "$497", ...selfGuided },

  ];
  return (
    <section className="demo-offers" aria-labelledby={`${product}-offer-heading`}>
      <div className="demo-offers-heading">
        <p className="bfg-eyebrow">{offerEyebrow ?? "CHOOSE HOW YOU WOULD LIKE TO MOVE FORWARD"}</p>
        <h2 id={`${product}-offer-heading`}>{offerHeading&&!/level|choose/i.test(offerHeading)?publicText(offerHeading):"Your Activation Call and Platform Access"}</h2>
        <p>{intro && !/\bor\b.*(?:professional|support|Rooney)/i.test(intro)?publicText(intro):"Begin during your activation call, then use your prepared dashboard to continue independently."}</p>
      </div>
      <div className="demo-offer-grid">
        {cards.map((card) => (
          <article className={`demo-offer-card ${card.key === "supported" ? "featured" : ""}`} key={card.key}>
            <p className="demo-offer-label">{card.label}</p>
            <h3>{publicText(card.title)}</h3>
            <p className="demo-offer-description">{publicText(card.description)}</p>
            <ul>{card.features.map((item) => <li key={item}><CheckCircle2 size={18}/><span>{publicText(item)}</span></li>)}</ul>
            <div className="demo-guarantee"><strong>100% Guarantee</strong></div>

            <button className="bfg-btn bfg-btn-primary" disabled={Boolean(busy) || disabled} onClick={() => onBuy(card.key)} data-testid={`${product}-${card.key}-buy`}>
              {busy === card.key ? "OPENING SECURE CHECKOUT…" : card.button}
            </button>
          </article>
        ))}
      </div>
      {error && <p className="bfg-error demo-offer-error">{error}</p>}
    </section>
  );
}

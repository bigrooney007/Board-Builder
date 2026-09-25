import { CheckCircle2 } from "lucide-react";
import "./demo-offers.css";

export default function DemoOfferCards({ product, selfGuided, supported, busy, disabled = false, onBuy, error }) {
  const cards = [
    { key: "self-guided", label: "SELF-GUIDED PATHWAY", price: "$497", ...selfGuided },
    { key: "supported", label: "WORK WITH ROONEY", ...supported },
  ];
  return (
    <section className="demo-offers" aria-labelledby={`${product}-offer-heading`}>
      <div className="demo-offers-heading">
        <p className="bfg-eyebrow">CHOOSE HOW YOU WOULD LIKE TO MOVE FORWARD</p>
        <h2 id={`${product}-offer-heading`}>Choose The Level Of Support That Is Right For You</h2>
        <p>Use the complete platform with your board, or work directly with Rooney to guide the process with you.</p>
      </div>
      <div className="demo-offer-grid">
        {cards.map((card) => (
          <article className={`demo-offer-card ${card.key === "supported" ? "featured" : ""}`} key={card.key}>
            <p className="demo-offer-label">{card.label}</p>
            <h3>{card.title}</h3>
            <p className="demo-offer-description">{card.description}</p>
            <ul>{card.features.map((item) => <li key={item}><CheckCircle2 size={18}/><span>{item}</span></li>)}</ul>
            {card.guarantee && <div className="demo-guarantee"><strong>100% Outcome Guarantee</strong><span>{card.guarantee}</span></div>}
            <div className="demo-offer-price">{card.price}<small> ONE TIME</small></div>
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

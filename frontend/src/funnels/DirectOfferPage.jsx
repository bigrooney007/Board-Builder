import { useEffect } from "react";
import { FunnelLayout } from "./FunnelLayout";
import { OfferPurchaseBlock, RESULTS } from "./BoardFixDiagnostic";

// Stable direct-entry payment pages. Each renders the SAME offer/payment block
// used on the diagnostic result — no duplicated checkout logic.
export default function DirectOfferPage({ pathway }) {
  const result = RESULTS[pathway];

  useEffect(() => { document.title = `${result.offerName} | Nonprofit Board Builder`; }, [result.offerName]);

  return (
    <FunnelLayout restrained>
      <main className="offer-sales-page" data-testid={`direct-offer-page-${pathway}`}>
        <header className="funnel-hero-banner offer-sales-banner" data-testid={`direct-offer-hero-${pathway}`}>
          <h1 data-testid={`direct-offer-headline-${pathway}`}>{result.offerName}</h1>
          <i aria-hidden="true" />
        </header>
        <div className="offer-sales-container">
          <OfferPurchaseBlock recommendation={pathway} />
        </div>
      </main>
    </FunnelLayout>
  );
}

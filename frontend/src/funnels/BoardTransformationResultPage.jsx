import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { SITE_CONTENT } from "@/content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const OFFERS = [
  { key: "recruit", contentKey: "recruitment", route: "/offer/recruitment", testid: "bt-choose-recruit" },
  { key: "reactivate", contentKey: "reactivation", route: "/offer/reactivation", testid: "bt-choose-reactivate" },
  { key: "activate", contentKey: "activation", route: "/offer/activation", testid: "bt-choose-activate" },
];

export default function BoardTransformationResultPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    axios.get(`${API}/funnel-leads/result/${token}`)
      .then((response) => setResult(response.data))
      .catch(() => setError("We could not load your result. Please check your link."));
  }, [token]);

  const choose = async (product, route) => {
    try { sessionStorage.setItem("bt_result_token", token); } catch { /* storage is best-effort */ }
    try { await axios.post(`${API}/funnel-leads/board-transformation/select`, { result_token: token, product }); } catch { /* selection is best-effort */ }
    navigate(route);
  };

  const content = SITE_CONTENT.boardTransformationResult;

  return (
    <FunnelLayout restrained>
      <main data-testid="board-transformation-result-page" style={{ maxWidth: 900, margin: "0 auto", padding: "48px 20px" }}>
        {error && <p className="submit-error" data-testid="bt-result-error">{error}</p>}
        {result && (
          <>
            <header style={{ marginBottom: 26, textAlign: "center" }}>
              <p className="eyebrow">Prepared for {result.organization}</p>
              <h1 className="video-page-title" data-testid="bt-result-headline">{content.headline}</h1>
            </header>

            <div className="video-stage" data-testid="bt-result-video">
              <span data-testid="bt-result-video-placeholder">{content.videoPlaceholder}</span>
            </div>

            <section data-testid="bt-result-choice">
              <h2 style={{ textAlign: "center" }} data-testid="bt-result-choose-heading">{content.chooseHeading}</h2>
              <div className="offer-choice-grid">
                {OFFERS.map((offer) => {
                  const recommended = (result.result?.recommendations || []).includes(offer.key);
                  return (
                    <div key={offer.key} className="offer-choice-cell">
                      {recommended && <span className="offer-recommended-badge" data-testid={`bt-recommended-badge-${offer.key}`}>{content.recommendedBadge}</span>}
                      <button type="button" className="button" onClick={() => choose(offer.key, offer.route)} data-testid={offer.testid}>
                        {content.offers[offer.contentKey]}
                      </button>
                    </div>
                  );
                })}
              </div>
            </section>

            <div style={{ marginTop: 40 }}>
              <TestimonialCarousel idPrefix="bt-result" />
            </div>
          </>
        )}
      </main>
    </FunnelLayout>
  );
}

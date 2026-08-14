import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { FunnelLayout } from "./FunnelLayout";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const FRAMEWORK = [
  { number: "1", title: "Recruit", text: "Bring the right people around the table." },
  { number: "2", title: "Reactivate", text: "Get the people already there to stand up or step down." },
  { number: "3", title: "Activate", text: "Turn your Board into fundraising champions for your mission." },
];

const RECOMMENDATION_COPY = {
  reactivate: { title: "Reactivate Your Board", text: "You have Board Members who are not currently active. Give every current Board Member a clear opportunity to recommit, have the conversations that need to happen, and give the people who remain clear responsibility." },
  recruit: { title: "Recruit New Board Members", text: "Your organization needs more of the right people around the table. Identify the skills, experience and relationships your Board is missing and recruit the Board Members who fill those gaps." },
  activate: { title: "Activate Your Board Around Fundraising", text: "You want your Board Members to actively help raise money. Turn your Board into fundraising champions with clear, person-specific fundraising responsibility." },
};

const CARDS = [
  { key: "recruit", title: "RECRUIT MY BOARD", route: "/recruit-with-rooney", testid: "bt-result-recruit-card" },
  { key: "reactivate", title: "REACTIVATE MY BOARD", route: "/reactivate-with-rooney", testid: "bt-result-reactivate-card" },
  { key: "activate", title: "ACTIVATE MY BOARD", route: "/activate-with-rooney", testid: "bt-result-activate-card" },
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
    try { await axios.post(`${API}/funnel-leads/board-transformation/select`, { result_token: token, product }); } catch { /* selection is best-effort */ }
    navigate(route);
  };

  const recommendations = result?.result?.recommendations || [];

  return (
    <FunnelLayout restrained>
      <main data-testid="board-transformation-result-page" style={{ maxWidth: 860, margin: "0 auto", padding: "48px 20px" }}>
        {error && <p className="submit-error" data-testid="bt-result-error">{error}</p>}
        {result && (
          <>
            <header style={{ marginBottom: 30 }}>
              <p className="eyebrow">Prepared for {result.organization}</p>
              <h1 data-testid="bt-result-headline">Your Board Transformation Journey</h1>
            </header>

            <section data-testid="bt-result-framework" style={{ marginBottom: 34 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
                {FRAMEWORK.map((stage) => (
                  <article className="member-card" key={stage.title} data-testid={`bt-framework-${stage.title.toLowerCase()}`}>
                    <p className="eyebrow" style={{ margin: 0 }}>{stage.number}</p>
                    <h3 style={{ margin: "6px 0" }}>{stage.title}</h3>
                    <p style={{ margin: 0 }}>{stage.text}</p>
                  </article>
                ))}
              </div>
            </section>

            <section data-testid="bt-result-recommendations" style={{ marginBottom: 34 }}>
              <h2>Based on What You Told Us</h2>
              {recommendations.length === 0 && (
                <p data-testid="bt-no-recommendation">Based on your answers, your Board is in a solid position. You can still strengthen it — choose the area you want to work on below.</p>
              )}
              {recommendations.map((key, index) => (
                <article className="member-card" key={key} data-testid={`bt-recommendation-${key}`} style={{ marginBottom: 12 }}>
                  <p className="eyebrow" style={{ margin: 0 }}>Step {index + 1}</p>
                  <h3 style={{ margin: "6px 0" }}>{RECOMMENDATION_COPY[key].title}</h3>
                  <p style={{ margin: 0 }}>{RECOMMENDATION_COPY[key].text}</p>
                </article>
              ))}
            </section>

            <section data-testid="bt-result-choice">
              <h2>Which Would You Like to Do First?</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
                {CARDS.map((card) => (
                  <article className="member-card" key={card.key} data-testid={card.testid}>
                    <h3 style={{ marginTop: 0 }}>{RECOMMENDATION_COPY[card.key].title}</h3>
                    {recommendations.includes(card.key) && <p className="eyebrow" data-testid={`bt-recommended-badge-${card.key}`}>Recommended for your Board</p>}
                    <button className="button" onClick={() => choose(card.key, card.route)} data-testid={`bt-choose-${card.key}`}>{card.title}</button>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
      </main>
    </FunnelLayout>
  );
}

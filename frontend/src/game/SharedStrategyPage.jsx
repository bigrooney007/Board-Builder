import { useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import { MODE_LABELS, StrategyDocument } from "./strategyRender";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function SharedStrategyPage() {
  const { shareToken } = useParams();
  const [strategy, setStrategy] = useState(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    document.title = "Fundraising Strategy";
    axios.get(`${API}/strategy/shared/${shareToken}`)
      .then((response) => setStrategy(response.data.strategy))
      .catch(() => setNotFound(true));
  }, [shareToken]);

  if (notFound) {
    return (
      <div className="bfg bfg-gg" style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 20 }}>
        <div className="bfg-gg-card" style={{ maxWidth: 420, textAlign: "center" }} data-testid="bfg-shared-invalid">
          <h2>This Strategy Link Is Not Valid</h2>
          <p>Please ask the organisation to share the current strategy link.</p>
        </div>
      </div>
    );
  }
  if (!strategy) return <div className="bfg bfg-gg" style={{ minHeight: "100vh" }} />;

  return (
    <div className="bfg bfg-gg" style={{ minHeight: "100vh" }} data-testid="bfg-shared-strategy-page">
      <header className="bfg-gg-nav">
        <span><strong>{strategy.organization_name} Fundraising Strategy</strong> · {MODE_LABELS[strategy.mode] || strategy.mode}</span>
      </header>
      <main style={{ maxWidth: 860, margin: "0 auto", padding: "24px 16px 70px" }}>
        <StrategyDocument strategy={strategy} />
      </main>
    </div>
  );
}

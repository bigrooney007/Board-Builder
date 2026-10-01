import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { FunnelLayout } from "@/funnels/FunnelLayout";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function BoardApplicantMarketplace() {
  const [list, setList] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    document.title = "Board Applicant Marketplace | Nonprofit Board Builder";
    axios.get(`${API}/public/board-opportunities`).then(({ data }) => setList(data.opportunities || []))
      .catch(() => setError("Board opportunities are temporarily unavailable. Please try again."));
  }, []);
  return <FunnelLayout><main className="member-page public-opportunity-page" data-testid="board-applicant-marketplace">
    <header className="member-page-heading"><p className="eyebrow">BOARD APPLICANT MARKETPLACE</p>
      <h1>Find A Nonprofit Board Opportunity</h1>
      <p>Explore live board opportunities and apply directly to the organization through its Board Builder application.</p>
      <Link to="/join-a-board">Join the Board Applicant Network for future opportunities</Link>
    </header>
    {error && <p className="submit-error">{error}</p>}
    {!error && !list.length && <section className="member-card"><p>No board opportunities are live at the moment. Join the Applicant Network to hear about new openings.</p></section>}
    {list.map((item) => <article className="workspace-panel" key={item.slug} data-testid={`marketplace-${item.slug}`}>
      <p className="eyebrow">BOARD OPPORTUNITY{item.location ? ` · ${item.location}` : ""}</p>
      <h2>{item.organization_name}</h2>
      {item.mission && <p><strong>Mission:</strong> {item.mission}</p>}
      {item.summary && <p>{item.summary}</p>}
      {item.roles_sought && <p><strong>Who they seek:</strong> {item.roles_sought}</p>}
      {item.expectations && <p><strong>Board expectations:</strong> {item.expectations}</p>}
      <Link className="button" to={`/board-opportunities/${item.slug}/apply`}>APPLY</Link>
    </article>)}
  </main></FunnelLayout>;
}

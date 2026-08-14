import { Link } from "react-router-dom";
import { PlayCircle } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";

export default function ActivateWithRooneyPage() {
  return (
    <FunnelLayout restrained>
      <main data-testid="activate-with-rooney-page" style={{ maxWidth: 760, margin: "0 auto", padding: "48px 20px" }}>
        <header style={{ marginBottom: 26 }}>
          <p className="eyebrow">Board Activation</p>
          <h1 data-testid="awr-headline">Activate Your Board</h1>
          <p data-testid="awr-supporting">Turn your Board into fundraising champions who help carry the fundraising responsibility for your mission.</p>
        </header>
        <div className="module-video placeholder" data-testid="awr-video-placeholder">
          <PlayCircle size={38} />
          <h3>Board Activation Video Coming Soon</h3>
          <p>The Board Activation training video will appear here as soon as it is published.</p>
        </div>
        <section className="member-card" style={{ marginTop: 26 }} data-testid="awr-coming-soon">
          <h2>The Full Board Activation Experience Is Coming Soon</h2>
          <p>We are finishing the complete Board Activation program. In the meantime, you can start with the part of the Board Transformation journey your Board needs most.</p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <Link className="button" to="/board-transformation" data-testid="awr-diagnostic-button">TELL ME WHAT MY BOARD NEEDS</Link>
            <Link className="button button-back" to="/" data-testid="awr-home-button">Back to Home</Link>
          </div>
        </section>
      </main>
    </FunnelLayout>
  );
}

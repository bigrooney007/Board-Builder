import { ExternalLink, PlayCircle } from "lucide-react";
import { usePlatformVideo } from "./platform";
import "./dashboard-walkthrough.css";

const VIDEOS = {
  recruitment: ["recruitment_dashboard", "recruitment_welcome"],
  "board-fundraising-game": ["game_dashboard", "game_welcome"],
  "strategic-planning": ["strategic_planning_dashboard", "strategic_planning_welcome"],
  "board-recommitment": ["board_recommitment_dashboard", "board_recommitment_welcome"],
};

export default function DashboardWalkthroughVideo({ flow }) {
  const [key, fallbackKey] = VIDEOS[flow];
  const video = usePlatformVideo(key, fallbackKey);

  return <section className="dashboard-walkthrough" aria-label="Dashboard video walkthrough" data-testid={`${flow}-dashboard-walkthrough`}>
    <div className="dashboard-walkthrough-copy">
      <PlayCircle size={28} aria-hidden="true" />
      <div>
        <strong>Watch How To Use This Dashboard</strong>
        <p>Follow Rooney through the full process. Return to this video whenever you need help.</p>
      </div>
    </div>
    {video?.youtube_id ? <a className="dashboard-walkthrough-link" href={`https://www.youtube.com/watch?v=${video.youtube_id}`} target="_blank" rel="noopener noreferrer">
      Watch The Walkthrough <ExternalLink size={16} aria-hidden="true" />
    </a> : <p className="dashboard-walkthrough-pending">Dashboard video coming soon</p>}
  </section>;
}

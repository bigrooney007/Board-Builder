import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useMemberAuth } from "./MemberAuthContext";

export const BoardFixContinuation = ({ label, to }) => {
  const { member } = useMemberAuth();
  if (!member?.entitlements?.includes("board_fix_system")) return null;
  return (
    <section className="member-card" data-testid="board-fix-continuation">
      <p className="eyebrow">Complete Board Fix</p>
      <p>When you have finished this stage, keep moving. Your Board Fix journey continues.</p>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Link className="button" to={to} data-testid="board-fix-continuation-link">{label} <ArrowRight size={16} /></Link>
        <Link className="button button-outline" to="/board-fix-roadmap" data-testid="board-fix-continuation-roadmap">Return to My Board Fix Roadmap</Link>
      </div>
    </section>
  );
};

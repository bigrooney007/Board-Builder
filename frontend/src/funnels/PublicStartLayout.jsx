import { useEffect } from "react";
import { Link } from "react-router-dom";
import { BfgShell } from "@/game/gameShared";
import "./public-start.css";

export default function PublicStartLayout({ children, backTo, backLabel, testId, className = "" }) {
  useEffect(() => { window.scrollTo({ top: 0 }); }, []);
  return (
    <BfgShell shellClass="public-start-shell">
      <main className={`public-start-page ${className}`.trim()} data-testid={testId}>
        {children}
        <p className="public-start-back"><Link to={backTo}>{backLabel}</Link></p>
      </main>
    </BfgShell>
  );
}

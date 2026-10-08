import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useFlowVideo } from "@/hooks/useFlowVideos";
import { BfgShell, GameVideo } from "./gameShared";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PUBLIC_START_ROUTES } from "@/funnels/publicStartRoutes";
import "./game-landing.css";

export default function GameDemonstrationPage() {
  const { member } = useMemberAuth();
  const [searchParams] = useSearchParams();
  const configuredVideo = useFlowVideo("game_homepage");
  // The live demonstration remains available if a preview has no copied video setting.
  const video = configuredVideo?.youtube_id ? configuredVideo : {
    key: "game_homepage", youtube_id: "iHr6ddUsp9Y", url: "https://youtu.be/iHr6ddUsp9Y",
  };
  const [continuePath, setContinuePath] = useState(PUBLIC_START_ROUTES["board-fundraising-game"]);

  useEffect(() => { document.title = "See How The Board Fundraising Game Works"; }, []);
  useEffect(() => {
    if (!member) { setContinuePath(PUBLIC_START_ROUTES["board-fundraising-game"]); return; }
    let active = true;
    memberApi.get("/game/free").then(({ data }) => {
      if (active) setContinuePath(data.unlocked ? "/game/setup" : data.complete ? "/game/upgrade" : "/game/questions");
    }).catch(() => { if (active) setContinuePath(PUBLIC_START_ROUTES["board-fundraising-game"]); });
    return () => { active = false; };
  }, [member]);

  return (
    <BfgShell>
      <main className="bfg-flow bfg-demo-page" style={{ maxWidth: 1120, margin: "0 auto", padding: "40px 20px 90px", textAlign: "center" }} data-testid="bfg-demonstration-page">
        <p className="bfg-eyebrow">SEE THE BOARD FUNDRAISING GAME IN ACTION</p>
        <h1 style={{ fontSize: "clamp(30px, 6vw, 48px)", lineHeight: 1.08 }}>See Exactly How You And Your Board Will Use The Platform</h1>
        <p style={{ margin: "16px auto 0", maxWidth: 650, fontSize: 18 }}>
          Watch Rooney take you through the Board Fundraising Game and show you how your board moves from a fundraising goal to a clear fundraising strategy, individual board roles and the tools needed to execute.
        </p>
        {searchParams.get("checkout") === "cancelled" && (
          <p className="bfg-error" style={{ marginTop: 16 }} data-testid="bfg-demonstration-checkout-cancelled">
            Your checkout was cancelled. You have not been charged.
          </p>
        )}
        <div style={{ marginTop: 26 }}><GameVideo video={video} testId="bfg-demonstration-video" /></div>
        <p style={{ margin: "26px auto 20px", maxWidth: 700 }}>
          Start with your fundraising goal and share your own thinking in five questions. Then bring your board into the process.
        </p>
        <Link className="bfg-btn bfg-btn-primary" to={continuePath} data-testid="bfg-demo-continue">
          {continuePath === "/game/upgrade" ? "CONTINUE MY BOARD FUNDRAISING GAME" : continuePath === "/game/setup" ? "OPEN MY BOARD FUNDRAISING GAME" : "START MY BOARD FUNDRAISING GAME"}
        </Link>
        <TestimonialCarousel heading="What Nonprofit Leaders We Have Worked With Are Saying" idPrefix="fundraising-game-demo"/>
      </main>
    </BfgShell>
  );
}

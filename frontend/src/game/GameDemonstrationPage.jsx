import { useEffect, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useFlowVideo } from "@/hooks/useFlowVideos";
import { BfgShell, GameVideo } from "./gameShared";
import { trackPlatformEvent } from "@/clean/platform";
import { useMemberAuth } from "@/member/MemberAuthContext";
import DemoOfferCards from "@/components/DemoOfferCards";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";

export default function GameDemonstrationPage() {
  const { member, loading } = useMemberAuth();
  const [searchParams] = useSearchParams();
  const video = useFlowVideo("game_homepage");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { document.title = "See How The Board Fundraising Game Works"; }, []);

  if (loading) return <div className="bfg" style={{ minHeight: "100vh" }} />;
  if (!member) return <Navigate to="/board-fundraising-game" replace />;

  const buy = async (pathway = "self-guided") => {
    setBusy(pathway); setError("");
    try {
      const organization = sessionStorage.getItem("bfgOrg") || "";
      const amount = Number(sessionStorage.getItem("bfgGoal") || 0);
      const fullName = sessionStorage.getItem("bfgName") || [member.first_name, member.last_name].filter(Boolean).join(" ");
      if (organization && amount && fullName) {
        await memberApi.put("/game/profile", {
          organization: { name: organization },
          goal: { amount, purpose: "Reach our fundraising goal" },
          primary_user: { full_name: fullName, email: member.email || "" },
        });
      }
      trackPlatformEvent("board-fundraising-game", "checkout_started");
      const response = pathway === "supported"
        ? await memberApi.post("/payments/supported-checkout", { product:"board-fundraising-game", origin_url:window.location.origin })
        : await memberApi.post("/payments/game-checkout", { origin_url: window.location.origin, cancel_path: "/game/demonstration" });
      window.location.href = response.data.checkout_url;
    } catch {
      setError("We could not open checkout. Please try again.");
      setBusy("");
    }
  };

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 1120, margin: "0 auto", padding: "40px 20px 90px", textAlign: "center" }} data-testid="bfg-demonstration-page">
        <p className="bfg-eyebrow">SEE THE BOARD FUNDRAISING GAME IN ACTION</p>
        <h1 style={{ fontSize: "clamp(30px, 6vw, 48px)", lineHeight: 1.08 }}>See Exactly How You And Your Board Will Use The Platform</h1>
        <p style={{ margin: "16px auto 0", maxWidth: 650, fontSize: 17 }}>
          Watch Rooney take you through the Board Fundraising Game and show you how your board moves from a fundraising goal to a clear fundraising strategy, individual board roles and the tools needed to execute.
        </p>
        {searchParams.get("checkout") === "cancelled" && (
          <p className="bfg-error" style={{ marginTop: 16 }} data-testid="bfg-demonstration-checkout-cancelled">
            Your checkout was cancelled. You have not been charged.
          </p>
        )}
        <div style={{ marginTop: 26 }}><GameVideo video={video} testId="bfg-demonstration-video" /></div>
        <DemoOfferCards product="board-fundraising-game" busy={busy} onBuy={buy} error={error}
          selfGuided={{title:"Run The Board Fundraising Game With Your Board",description:"Use the platform to guide your board from individual ideas to one adopted fundraising strategy.",features:["Get every Board Member's original fundraising ideas","Facilitate the live group game with the built-in guide","Create, edit and adopt a practical fundraising strategy","Delegate roles and give every member their Portfolio and Executive Assistant"],guarantee:"Complete the Board Fundraising Game and follow the guided process. If the platform does not help your board produce a usable fundraising strategy you can begin executing, tell us and we will refund 100% of your purchase.",button:"START MY SELF-GUIDED GAME — $497"}}
          supported={{title:"Run Your Board Fundraising Game With Rooney",description:"Rooney works with you and your board to facilitate the process and turn the decisions into action.",features:["Prepare your organization and Board Members for the game","Facilitate the live Board Fundraising Game","Create the final fundraising strategy from the Board's decisions","Help delegate the agreed roles so the Board can start raising money"],price:"$2,997",button:"WORK WITH ROONEY — $2,997"}}/>
        <TestimonialCarousel heading="What Nonprofit Leaders We Have Worked With Are Saying" idPrefix="fundraising-game-demo"/>
      </main>
    </BfgShell>
  );
}

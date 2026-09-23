import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import "@/App.css";

import MainHomePage from "@/pages/MainHomePage";
import JoinBoardPage from "@/pages/JoinBoardPage";
import AdminPage from "@/pages/AdminPage";
import LegalPage from "@/pages/LegalPage";
import { BlogPage, BlogPostPage } from "@/pages/BlogPages";

import RecruitFreePage from "@/funnels/RecruitFreePage";
import RecruitWalkthroughPage from "@/funnels/RecruitWalkthroughPage";
import RecruitWelcomePage from "@/funnels/RecruitWelcomePage";
import BoardRecommitmentFormPage from "@/funnels/BoardRecommitmentFormPage";
import PortfolioPage from "@/pages/PortfolioPage";

import {
  GuidedLandingPage,
  GuidedVideoPage,
  GuidedPaymentConfirmedPage,
  GuidedWelcomePage,
  GuidedIntakePage,
  GuidedDashboardPage,
} from "@/funnels/GuidedProductPages";
import StrategicPlanningFormPage from "@/funnels/StrategicPlanningFormPage";
import CommunityNeedResearchPage from "@/funnels/CommunityNeedResearchPage";
import StrategicPlanningResponsePage from "@/funnels/StrategicPlanningResponsePage";
import StrategicPlanReviewPage from "@/funnels/StrategicPlanReviewPage";
import AreaPackPage from "@/funnels/AreaPackPage";
import PublicStrategicPlanPage, { PublicActionPlanPage } from "@/funnels/PublicStrategicPlanPage";
import StrategicLeadershipPortfolioPage from "@/funnels/StrategicLeadershipPortfolioPage";
import StrategicLeadershipAssistantPage from "@/funnels/StrategicLeadershipAssistantPage";
import StrategicSessionWatchPage from "@/funnels/StrategicSessionWatchPage";
import StrategicPlanningSessionPage from "@/funnels/StrategicPlanningSessionPage";
import StrategicPresentationWatchPage from "@/funnels/StrategicPresentationWatchPage";

import { MemberAuthProvider } from "@/member/MemberAuthContext";
import { LoginPage, ForgotPasswordPage, ResetPasswordPage } from "@/member/AuthPages";
import { PurchaseSuccessPage } from "@/member/PurchaseSuccessPage";
import BoardRecruitmentPage from "@/member/BoardRecruitmentPage";
import RecruitmentGamePage from "@/member/RecruitmentGamePage";
import RecruitmentOnboardingSessionPage from "@/member/RecruitmentOnboardingSessionPage";
import RecruitmentOnboardingWatchPage from "@/public/RecruitmentOnboardingWatchPage";
import RecruitmentResultsPage from "@/member/workspace/ResultsPage";
import { MaterialsLibraryPage } from "@/member/workspace/MaterialsLibrary";
import SelectionOfferPage from "@/member/SelectionOfferPage";

import { OpportunityApplyPage, SavedProfileApplyPage, SignAgreementPage } from "@/public/OpportunityPages";
import { SharedResourcePage, BoardProfileFormPage } from "@/pages/SharedPages";
import CandidateReferenceFormPage, { RefereeFormPage } from "@/public/ReferencePages";

import GameHomePage from "@/game/GameHomePage";
import GameDemonstrationPage from "@/game/GameDemonstrationPage";
import GameAuthCallback from "@/game/GameAuthCallback";
import GameSituationPage from "@/game/GameSituationPage";
import GameWelcomePage from "@/game/GameWelcomePage";
import GameDashboardPage from "@/game/GameDashboardPage";
import GamePlayPage from "@/game/GamePlayPage";
import GroupGamePage from "@/game/GroupGamePage";
import StrategyPage from "@/game/StrategyPage";
import SharedStrategyPage from "@/game/SharedStrategyPage";
import GroupPlayPage from "@/game/GroupPlayPage";
import PortfoliosPage from "@/game/PortfoliosPage";
import PortfolioEditPage from "@/game/PortfolioEditPage";
import PortfolioToolkitPage from "@/game/PortfolioToolkitPage";
import BoardPortfolioPage from "@/game/BoardPortfolioPage";
import BoardExecutionAssistantPage from "@/game/BoardExecutionAssistantPage";
import HostCallScriptPage from "@/game/HostCallScriptPage";
import HostFacilitationPage from "@/game/HostFacilitationPage";
import HostChecklistPage from "@/game/HostChecklistPage";
import GameNightCompletePage from "@/game/GameNightCompletePage";
import FacilitatedGamePage from "@/game/FacilitatedGamePage";
import FacilitatedGameApplicationPage from "@/game/FacilitatedGameApplicationPage";
import RelationshipMapDashboardPage from "@/game/RelationshipMapDashboardPage";
import RelationshipMappingPage from "@/game/RelationshipMappingPage";
import FinalStrategyMemberPage from "@/game/FinalStrategyMemberPage";

import PlatformAnalytics from "@/clean/PlatformAnalytics";

const CENTERED_PATHS = new Set([
  "/recruit",
  "/recruit/walkthrough",
  "/recruit/welcome",
  "/board-fundraising-game",
  "/strategic-planning",
  "/board-recommitment",
  "/organize-board-fundraising-game",
  "/organize-board-fundraising-game/apply",
]);

function PublicCenteringScope() {
  const { pathname } = useLocation();
  useEffect(() => {
    document.body.classList.toggle("public-centered", CENTERED_PATHS.has(pathname));
    return () => document.body.classList.remove("public-centered");
  }, [pathname]);
  return null;
}

function GoogleAuthGate({ children }) {
  const location = useLocation();
  if (location.hash && location.hash.includes("session_id=")) return <GameAuthCallback />;
  return children;
}

function CleanRoutes() {
  return (
    <Routes>
      <Route path="/" element={<MainHomePage />} />

      {/* Board Recruitment */}
      <Route path="/recruit" element={<RecruitFreePage />} />
      <Route path="/recruit/walkthrough" element={<RecruitWalkthroughPage />} />
      <Route path="/recruit/welcome" element={<RecruitWelcomePage />} />
      <Route path="/purchase/success" element={<PurchaseSuccessPage />} />
      <Route path="/app/board-recruitment" element={<BoardRecruitmentPage />} />
      <Route path="/app/board-recruitment/questions" element={<RecruitmentGamePage />} />\n      <Route path="/app/board-recruitment/game" element={<Navigate to="/app/board-recruitment/questions" replace />} />
      <Route path="/app/board-recruitment/onboarding-session" element={<RecruitmentOnboardingSessionPage />} />
      <Route path="/onboarding-session/:token" element={<RecruitmentOnboardingWatchPage />} />
      <Route path="/app/recruitment/self-guided/results" element={<RecruitmentResultsPage />} />
      <Route path="/app/recruitment/self-guided/materials" element={<MaterialsLibraryPage />} />
      <Route path="/app/recruitment/selection-offer" element={<SelectionOfferPage />} />
      <Route path="/board-opportunities/:slug/apply" element={<OpportunityApplyPage />} />
      <Route path="/apply/:token" element={<SavedProfileApplyPage />} />
      <Route path="/sign/:token" element={<SignAgreementPage />} />
      <Route path="/shared/:token" element={<SharedResourcePage />} />
      <Route path="/board-profile/:token" element={<BoardProfileFormPage />} />
      <Route path="/reference-form/:token" element={<CandidateReferenceFormPage />} />
      <Route path="/referee-form/:token" element={<RefereeFormPage />} />

      {/* Board Fundraising Game */}
      <Route path="/board-fundraising-game" element={<GameHomePage />} />
      <Route path="/game/demonstration" element={<GameDemonstrationPage />} />
      <Route path="/game/welcome" element={<GameWelcomePage />} />
      <Route path="/game/setup" element={<GameSituationPage />} />
      <Route path="/game/dashboard" element={<GameDashboardPage />} />
      <Route path="/play/:token" element={<GamePlayPage />} />
      <Route path="/game/group" element={<GroupGamePage />} />
      <Route path="/group-game/:token" element={<GroupPlayPage />} />
      <Route path="/game/strategy/view/:strategyId" element={<StrategyPage />} />
      <Route path="/game/portfolios" element={<PortfoliosPage />} />
      <Route path="/game/portfolios/:portfolioId" element={<PortfolioEditPage />} />
      <Route path="/game/portfolios/:portfolioId/toolkit" element={<PortfolioToolkitPage />} />
      <Route path="/board-portfolio/:token" element={<BoardPortfolioPage />} />
      <Route path="/board-assistant/:token" element={<BoardExecutionAssistantPage />} />
      <Route path="/game/host/call-script" element={<HostCallScriptPage />} />
      <Route path="/game/host/facilitation" element={<HostFacilitationPage />} />
      <Route path="/game/host/checklist" element={<HostChecklistPage />} />
      <Route path="/game/complete" element={<GameNightCompletePage />} />
      <Route path="/game/relationships" element={<RelationshipMapDashboardPage />} />
      <Route path="/game/final/:token" element={<FinalStrategyMemberPage />} />
      <Route path="/relationship-mapping/:token" element={<RelationshipMappingPage />} />
      <Route path="/strategy/:shareToken" element={<SharedStrategyPage />} />
      <Route path="/game/signup" element={<Navigate to="/board-fundraising-game" replace />} />
      <Route path="/game/start" element={<Navigate to="/board-fundraising-game" replace />} />
      <Route path="/game/upgrade" element={<Navigate to="/game/demonstration" replace />} />
      <Route path="/game/unlock" element={<Navigate to="/game/demonstration" replace />} />
      <Route path="/game/board-review" element={<Navigate to="/game/dashboard" replace />} />
      <Route path="/game/meeting-review" element={<Navigate to="/game/dashboard" replace />} />
      <Route path="/game/meeting-review/decisions" element={<Navigate to="/game/dashboard" replace />} />
      <Route path="/game/meeting-review/final" element={<Navigate to="/game/dashboard" replace />} />
      <Route path="/game/strategy/priorities" element={<Navigate to="/game/dashboard" replace />} />
      <Route path="/game/execution-materials" element={<Navigate to="/game/portfolios" replace />} />

      {/* Facilitated Board Fundraising Game, application ends after submission */}
      <Route path="/organize-board-fundraising-game" element={<FacilitatedGamePage />} />
      <Route path="/organize-board-fundraising-game/apply" element={<FacilitatedGameApplicationPage />} />

      {/* Strategic Planning */}
      <Route path="/strategic-planning" element={<GuidedLandingPage product="strategic-planning" />} />
      <Route path="/strategic-planning/video" element={<GuidedVideoPage product="strategic-planning" />} />
      <Route path="/strategic-planning/payment-confirmed" element={<GuidedPaymentConfirmedPage product="strategic-planning" />} />
      <Route path="/strategic-planning/welcome" element={<GuidedWelcomePage product="strategic-planning" />} />
      <Route path="/strategic-planning/intake" element={<GuidedIntakePage product="strategic-planning" />} />
      <Route path="/strategic-planning/dashboard" element={<GuidedDashboardPage product="strategic-planning" />} />
      <Route path="/strategic-planning-form/:token" element={<StrategicPlanningFormPage />} />
      <Route path="/strategic-session/:token" element={<StrategicSessionWatchPage />} />
      <Route path="/strategic-planning/session" element={<StrategicPlanningSessionPage />} />
      <Route path="/strategic-presentation/:token" element={<StrategicPresentationWatchPage />} />
      <Route path="/community-need-research/:token" element={<CommunityNeedResearchPage />} />
      <Route path="/strategic-planning-response/:participantId" element={<StrategicPlanningResponsePage />} />
      <Route path="/strategic-plan-review/:token" element={<StrategicPlanReviewPage />} />
      <Route path="/area-pack/:token" element={<AreaPackPage />} />
      <Route path="/strategic-plan/:token" element={<PublicStrategicPlanPage />} />
      <Route path="/strategic-draft/:token" element={<PublicStrategicPlanPage endpoint="strategic-draft" />} />
      <Route path="/strategic-action-plan/:token" element={<PublicActionPlanPage />} />
      <Route path="/strategic-leadership-portfolio/:token" element={<StrategicLeadershipPortfolioPage />} />
      <Route path="/strategic-leadership-assistant/:token" element={<StrategicLeadershipAssistantPage />} />

      {/* Board Recommitment */}
      <Route path="/board-recommitment" element={<GuidedLandingPage product="board-recommitment" />} />
      <Route path="/board-recommitment/video" element={<GuidedVideoPage product="board-recommitment" />} />
      <Route path="/board-recommitment/payment-confirmed" element={<GuidedPaymentConfirmedPage product="board-recommitment" />} />
      <Route path="/board-recommitment/welcome" element={<GuidedWelcomePage product="board-recommitment" />} />
      <Route path="/board-recommitment/intake" element={<GuidedIntakePage product="board-recommitment" />} />
      <Route path="/board-recommitment/dashboard" element={<GuidedDashboardPage product="board-recommitment" />} />
      <Route path="/board-recommitment/:token" element={<BoardRecommitmentFormPage />} />
      <Route path="/portfolio/:token" element={<PortfolioPage />} />

      {/* Board Applicant Network */}
      <Route path="/join-a-board" element={<JoinBoardPage />} />

      {/* Authentication, admin and public support pages */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
      <Route path="/admin" element={<AdminPage />} />
      <Route path="/privacy-policy" element={<LegalPage type="privacy" />} />
      <Route path="/terms" element={<LegalPage type="terms" />} />
      <Route path="/blog" element={<BlogPage />} />
      <Route path="/blog/:slug" element={<BlogPostPage />} />

      {/* Legacy public product routes are intentionally disconnected from the clean house. */}
      <Route path="/app" element={<Navigate to="/" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <MemberAuthProvider>
        <PublicCenteringScope />
        <PlatformAnalytics />
        <GoogleAuthGate>
          <CleanRoutes />
        </GoogleAuthGate>
      </MemberAuthProvider>
    </BrowserRouter>
  );
}

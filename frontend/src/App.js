import { useEffect, useState } from "react";
import StrategicLeadershipPortfolioPage from "./funnels/StrategicLeadershipPortfolioPage";
import axios from "axios";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import "@/App.css";
import { LandingPage } from "@/components/LandingPage";
import { AssessmentForm } from "@/components/AssessmentForm";
import { ConfirmationScreen } from "@/components/ConfirmationScreen";
import JoinBoardPage from "@/pages/JoinBoardPage";
import AdminPage from "@/pages/AdminPage";
import LegalPage from "@/pages/LegalPage";
import MainHomePage from "@/pages/MainHomePage";
import RecruitWelcomePage from "@/funnels/RecruitWelcomePage";
import FunnelLandingPage from "@/funnels/FunnelLandingPage";
import RecruitFreePage from "@/funnels/RecruitFreePage";
import RecruitWalkthroughPage from "@/funnels/RecruitWalkthroughPage";
import FunnelResultPage from "@/funnels/FunnelResultPage";
import FunnelOptionsPage from "@/funnels/FunnelOptionsPage";
import BoardRecruitmentProposalPage, { BoardRecruitmentProposalConfirmedPage } from "@/funnels/BoardRecruitmentProposalPage";
import AboutRooneyPage from "@/funnels/AboutRooneyPage";
import BoardRecruitmentIntakePage from "@/funnels/BoardRecruitmentIntakePage";
import ReactivateWithRooneyPage from "@/funnels/ReactivateWithRooneyPage";
import ReactivateYourBoardYourselfPage from "@/funnels/ReactivateYourBoardYourselfPage";
import BoardReactivationProposalPage from "@/funnels/BoardReactivationProposalPage";
import BoardReactivationIntakePage from "@/funnels/BoardReactivationIntakePage";
import ReactivationStartHerePage from "@/funnels/ReactivationStartHerePage";
import BoardRecommitmentFormPage from "@/funnels/BoardRecommitmentFormPage";
import PortfolioPage from "@/pages/PortfolioPage";
import BoardTransformationPage from "@/funnels/BoardTransformationPage";
import BoardTransformationResultPage from "@/funnels/BoardTransformationResultPage";
import ActivateWithRooneyPage from "@/funnels/ActivateWithRooneyPage";
import ActivateYourBoardYourselfPage from "@/funnels/ActivateYourBoardYourselfPage";
import BoardActivationProposalPage from "@/funnels/BoardActivationProposalPage";
import BoardActivationIntakePage from "@/funnels/BoardActivationIntakePage";
import ActivationStartHerePage from "@/funnels/ActivationStartHerePage";
import PlanningFormPage from "@/funnels/PlanningFormPage";
import StrategyReviewPage from "@/funnels/StrategyReviewPage";
import StrategyPlanPage from "@/funnels/StrategyPlanPage";
import OfferVideoPage from "@/funnels/OfferVideoPage";
import DirectOfferPage from "@/funnels/DirectOfferPage";
import FundraisingPortfolioPage from "@/funnels/FundraisingPortfolioPage";
import CaseForSupportPage from "@/funnels/CaseForSupportPage";
import MyFundraisingBoardPage from "@/member/MyFundraisingBoardPage";
import ActivationStartPage from "@/member/ActivationStartPage";
import ActivationResourcesPage from "@/member/ActivationResourcesPage";
import { ReactivationOverviewPage, ReactivationModulePage } from "@/member/ReactivationCoursePages";
import { ActivationOverviewPage, ActivationModulePage } from "@/member/ActivationCoursePages";
import { MemberAuthProvider } from "@/member/MemberAuthContext";
import { LoginPage, ForgotPasswordPage, ResetPasswordPage } from "@/member/AuthPages";
import { PurchaseSuccessPage } from "@/member/PurchaseSuccessPage";
import { DashboardPage } from "@/member/DashboardPage";
import { CourseOverviewPage, CourseModulePage } from "@/member/CoursePages";
import { MaterialsLibraryPage } from "@/member/workspace/MaterialsLibrary";
import SelectionOfferPage from "@/member/SelectionOfferPage";
import BoardFixIntakePage from "@/funnels/BoardFixIntakePage";
import FundraisingBoardBuilderOfferPage from "@/funnels/FundraisingBoardBuilderOfferPage";
import WelcomePage from "@/member/WelcomePage";
import FundraisingActivationPage from "@/member/FundraisingActivationPage";
import BoardRecruitmentPage from "@/member/BoardRecruitmentPage";
import BoardFixRoadmapPage from "@/member/BoardFixRoadmapPage";
import BoardFixOrientationPage from "@/member/BoardFixOrientationPage";
import RecruitmentResultsPage from "@/member/workspace/ResultsPage";
import { OpportunityApplyPage, SavedProfileApplyPage, SignAgreementPage } from "@/public/OpportunityPages";
import { BlogPage, BlogPostPage } from "@/pages/BlogPages";
import { SharedResourcePage, BoardProfileFormPage } from "@/pages/SharedPages";
import CandidateReferenceFormPage, { RefereeFormPage } from "@/public/ReferencePages";
import { ReviewProgressTracker } from "@/reviewMode";
import { WorkspaceModeBanner } from "@/operatorMode";
import { GuidedLandingPage, GuidedVideoPage, GuidedPaymentConfirmedPage, GuidedWelcomePage, GuidedIntakePage, GuidedDashboardPage } from "@/funnels/GuidedProductPages";
import StrategicPlanningFormPage from "@/funnels/StrategicPlanningFormPage";
import CommunityNeedResearchPage from "@/funnels/CommunityNeedResearchPage";
import StrategicPlanningResponsePage from "@/funnels/StrategicPlanningResponsePage";
import StrategicPlanReviewPage from "@/funnels/StrategicPlanReviewPage";
import AreaPackPage from "@/funnels/AreaPackPage";
import PublicStrategicPlanPage, { PublicActionPlanPage } from "@/funnels/PublicStrategicPlanPage";
import { PAGE_META, usePageMeta } from "@/seo";
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
import PriorityReviewPage from "@/game/PriorityReviewPage";
import GroupPlayPage from "@/game/GroupPlayPage";
import MeetingReviewPage from "@/game/MeetingReviewPage";
import MeetingDecisionsPage from "@/game/MeetingDecisionsPage";
import FinalStrategyPage from "@/game/FinalStrategyPage";
import PortfoliosPage from "@/game/PortfoliosPage";
import PortfolioEditPage from "@/game/PortfolioEditPage";
import PortfolioToolkitPage from "@/game/PortfolioToolkitPage";
import BoardPortfolioPage from "@/game/BoardPortfolioPage";
import HostCallScriptPage from "@/game/HostCallScriptPage";
import HostFacilitationPage from "@/game/HostFacilitationPage";
import HostChecklistPage from "@/game/HostChecklistPage";
import GameNightCompletePage from "@/game/GameNightCompletePage";
import UnlockGamePage from "@/game/UnlockGamePage";
import FacilitatedGamePage from "@/game/FacilitatedGamePage";
import FacilitatedGameApplicationPage from "@/game/FacilitatedGameApplicationPage";
import BoardStrategyReviewPage from "@/game/BoardStrategyReviewPage";
import ExecutionMaterialsPage from "@/game/ExecutionMaterialsPage";
import RelationshipMapDashboardPage from "@/game/RelationshipMapDashboardPage";
import RelationshipMappingPage from "@/game/RelationshipMappingPage";
import FinalStrategyMemberPage from "@/game/FinalStrategyMemberPage";

const PUBLIC_CENTERED_PATHS = ["/fundraising-system", "/board-fix", "/board-fix-intake", "/board-fix-orientation", "/recruit", "/reactivate", "/activate", "/recruit/process", "/recruit-with-rooney", "/reactivate-with-rooney", "/activate-with-rooney", "/about-rooney", "/board-reactivation", "/board-recruitment", "/board-fundraising-activation", "/complete-board-transformation"];

const PublicCenteringScope = () => {
  const { pathname } = useLocation();
  useEffect(() => {
    const centered = PUBLIC_CENTERED_PATHS.includes(pathname) || pathname.startsWith("/offer/");
    document.body.classList.toggle("public-centered", centered);
  }, [pathname]);
  return null;
};

const HomeExperience = () => {
  useEffect(() => {
    axios.post(`${process.env.REACT_APP_BACKEND_URL}/api/funnel-metrics/page-view`, { page: "homepage" }).catch(() => {});
  }, []);
  usePageMeta(...PAGE_META.home);
  const navigate = useNavigate();
  return <LandingPage onJoin={() => navigate("/join-a-board")} />;
};

const GoogleAuthGate = ({ children }) => {
  const location = useLocation();
  if (location.hash && location.hash.includes("session_id=")) return <GameAuthCallback />;
  return children;
};

const LegacyAssessmentPage = () => {
  const [confirmation, setConfirmation] = useState(null);
  const navigate = useNavigate();
  if (confirmation) return <ConfirmationScreen confirmation={confirmation} onHome={() => navigate("/")} />;
  return <AssessmentForm onComplete={setConfirmation} onHome={() => navigate("/")} />;
};

export default function App() {
  return (
    <BrowserRouter>
      <MemberAuthProvider>
        <PublicCenteringScope />
        <ReviewProgressTracker />
        <WorkspaceModeBanner />
        <GoogleAuthGate>
        <Routes>
          <Route path="/" element={<MainHomePage />} />
          <Route path="/board-fundraising-game" element={<GameHomePage />} />
          <Route path="/fundraising-system" element={<Navigate to="/" replace />} />
          <Route path="/game/demonstration" element={<GameDemonstrationPage />} />
          <Route path="/game/signup" element={<Navigate to="/board-fundraising-game" replace />} />
          <Route path="/game/start" element={<Navigate to="/board-fundraising-game" replace />} />
          <Route path="/game/welcome" element={<GameWelcomePage />} />
          <Route path="/game/setup" element={<GameSituationPage />} />
          <Route path="/game/dashboard" element={<GameDashboardPage />} />
          <Route path="/play/:token" element={<GamePlayPage />} />
          <Route path="/game/group" element={<GroupGamePage />} />
          <Route path="/group-game/:token" element={<GroupPlayPage />} />
          <Route path="/game/strategy/priorities" element={<PriorityReviewPage />} />
          <Route path="/game/strategy/view/:strategyId" element={<StrategyPage />} />
          <Route path="/game/meeting-review" element={<MeetingReviewPage />} />
          <Route path="/game/meeting-review/decisions" element={<MeetingDecisionsPage />} />
          <Route path="/game/meeting-review/final" element={<FinalStrategyPage />} />
          <Route path="/game/portfolios" element={<PortfoliosPage />} />
          <Route path="/game/portfolios/:portfolioId" element={<PortfolioEditPage />} />
          <Route path="/game/portfolios/:portfolioId/toolkit" element={<PortfolioToolkitPage />} />
          <Route path="/board-portfolio/:token" element={<BoardPortfolioPage />} />
          <Route path="/game/host/call-script" element={<HostCallScriptPage />} />
          <Route path="/game/host/facilitation" element={<HostFacilitationPage />} />
          <Route path="/game/host/checklist" element={<HostChecklistPage />} />
          <Route path="/game/complete" element={<GameNightCompletePage />} />
          <Route path="/game/upgrade" element={<Navigate to="/game/unlock" replace />} />
          <Route path="/game/unlock" element={<UnlockGamePage />} />
          <Route path="/game/board-review" element={<BoardStrategyReviewPage />} />
          <Route path="/organize-board-fundraising-game" element={<FacilitatedGamePage />} />
          <Route path="/organize-board-fundraising-game/apply" element={<FacilitatedGameApplicationPage />} />
          <Route path="/game/execution-materials" element={<ExecutionMaterialsPage />} />
          <Route path="/game/relationships" element={<RelationshipMapDashboardPage />} />
          <Route path="/game/final/:token" element={<FinalStrategyMemberPage />} />
          <Route path="/relationship-mapping/:token" element={<RelationshipMappingPage />} />
          <Route path="/strategy/:shareToken" element={<SharedStrategyPage />} />
          <Route path="/board-assessment" element={<Navigate to="/" replace />} />
          <Route path="/board-transformation" element={<Navigate to="/" replace />} />
          <Route path="/board-transformation/result/:token" element={<BoardTransformationResultPage />} />
          <Route path="/activate-with-rooney" element={<Navigate to="/" replace />} />
          <Route path="/recruit" element={<RecruitFreePage />} />
          <Route path="/recruit/walkthrough" element={<RecruitWalkthroughPage />} />
          <Route path="/recruit/welcome" element={<RecruitWelcomePage />} />
          <Route path="/board-fix" element={<Navigate to="/" replace />} />
          <Route path="/offer/board-fix" element={<Navigate to="/" replace />} />
          <Route path="/offer/fundraising-board-builder" element={<Navigate to="/" replace />} />
          <Route path="/welcome" element={<Navigate to="/" replace />} />
          <Route path="/board-reactivation" element={<Navigate to="/" replace />} />
          <Route path="/board-recruitment" element={<Navigate to="/" replace />} />
          <Route path="/board-fundraising-activation" element={<Navigate to="/" replace />} />
          <Route path="/complete-board-transformation" element={<Navigate to="/" replace />} />
          <Route path="/board-fix-intake" element={<Navigate to="/" replace />} />
          <Route path="/board-fix-roadmap" element={<Navigate to="/" replace />} />
          <Route path="/board-fix-dashboard" element={<Navigate to="/" replace />} />
          <Route path="/board-fix-orientation" element={<Navigate to="/" replace />} />
          <Route path="/recruit/process" element={<Navigate to="/" replace />} />
          <Route path="/recruit/checkout" element={<Navigate to="/" replace />} />
          <Route path="/recruit-with-rooney" element={<Navigate to="/" replace />} />
          <Route path="/board-recruitment-proposal" element={<Navigate to="/" replace />} />
          <Route path="/board-recruitment-proposal/confirmed" element={<Navigate to="/" replace />} />
          <Route path="/about-rooney" element={<Navigate to="/" replace />} />
          <Route path="/recruit-your-board-yourself" element={<Navigate to="/" replace />} />
          <Route path="/board-recruitment-intake" element={<Navigate to="/" replace />} />
          <Route path="/recruitment-start-here" element={<Navigate to="/" replace />} />
          <Route path="/reactivate" element={<Navigate to="/" replace />} />
          <Route path="/reactivate-with-rooney" element={<Navigate to="/" replace />} />
          <Route path="/reactivate-your-board-yourself" element={<Navigate to="/" replace />} />
          <Route path="/board-reactivation-proposal" element={<Navigate to="/" replace />} />
          <Route path="/board-reactivation-intake" element={<Navigate to="/" replace />} />
          <Route path="/reactivation-start-here" element={<Navigate to="/" replace />} />
          <Route path="/board-recommitment" element={<GuidedLandingPage product="board-recommitment" />} />
          <Route path="/board-recommitment/video" element={<GuidedVideoPage product="board-recommitment" />} />
          <Route path="/board-recommitment/payment-confirmed" element={<GuidedPaymentConfirmedPage product="board-recommitment" />} />
          <Route path="/board-recommitment/welcome" element={<GuidedWelcomePage product="board-recommitment" />} />
          <Route path="/board-recommitment/intake" element={<GuidedIntakePage product="board-recommitment" />} />
          <Route path="/board-recommitment/dashboard" element={<GuidedDashboardPage product="board-recommitment" />} />
          <Route path="/board-recommitment/:token" element={<BoardRecommitmentFormPage />} />
          <Route path="/portfolio/:token" element={<PortfolioPage />} />
          <Route path="/app/reactivation/self-guided" element={<ReactivationOverviewPage />} />
          <Route path="/app/reactivation/self-guided/module/:moduleNumber" element={<ReactivationModulePage />} />
          <Route path="/activate" element={<Navigate to="/" replace />} />
          <Route path="/activate-your-board-yourself" element={<Navigate to="/" replace />} />
          <Route path="/board-activation-proposal" element={<Navigate to="/" replace />} />
          <Route path="/board-activation-intake" element={<Navigate to="/" replace />} />
          <Route path="/activation-start-here" element={<Navigate to="/" replace />} />
          <Route path="/planning-form/:token" element={<PlanningFormPage />} />
          <Route path="/strategy-review/:token" element={<StrategyReviewPage />} />
          <Route path="/strategy-plan/:token" element={<StrategyPlanPage />} />
          <Route path="/offer/recruitment" element={<Navigate to="/" replace />} />
          <Route path="/offer/reactivation" element={<Navigate to="/" replace />} />
          <Route path="/offer/activation" element={<Navigate to="/" replace />} />
          <Route path="/fundraising-portfolio/:token" element={<FundraisingPortfolioPage />} />
          <Route path="/case-for-support/:token" element={<CaseForSupportPage />} />
          <Route path="/app/activation/self-guided/my-fundraising-board" element={<MyFundraisingBoardPage />} />
          <Route path="/app/activation/start" element={<ActivationStartPage />} />
          <Route path="/app/activation/resources" element={<ActivationResourcesPage />} />
          <Route path="/app/activation/self-guided" element={<ActivationOverviewPage />} />
          <Route path="/app/activation/self-guided/module/:moduleNumber" element={<ActivationModulePage />} />
          <Route path="/reactivate/result/:token" element={<FunnelResultPage offerSource="reactivation" />} />
          <Route path="/activate/result/:token" element={<FunnelResultPage offerSource="fundraising_activation" />} />
          <Route path="/recruit/options" element={<Navigate to="/" replace />} />
          <Route path="/reactivate/options" element={<Navigate to="/" replace />} />
          <Route path="/activate/options" element={<Navigate to="/" replace />} />
          <Route path="/join-a-board" element={<JoinBoardPage />} />
          <Route path="/privacy-policy" element={<LegalPage type="privacy" />} />
          <Route path="/terms" element={<LegalPage type="terms" />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/purchase/success" element={<PurchaseSuccessPage />} />
          <Route path="/app/fundraising-activation" element={<FundraisingActivationPage />} />
          <Route path="/app/board-recruitment" element={<BoardRecruitmentPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
          <Route path="/app" element={<DashboardPage />} />
          <Route path="/app/recruitment/basic" element={<CourseOverviewPage productSlug="basic" />} />
          <Route path="/app/recruitment/basic/module/:moduleNumber" element={<CourseModulePage productSlug="basic" />} />
          <Route path="/app/recruitment/self-guided" element={<CourseOverviewPage productSlug="self-guided" />} />
          <Route path="/app/recruitment/self-guided/module/:moduleNumber" element={<CourseModulePage productSlug="self-guided" />} />
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
          <Route path="/strategic-planning" element={<GuidedLandingPage product="strategic-planning" />} />
          <Route path="/strategic-planning/video" element={<GuidedVideoPage product="strategic-planning" />} />
          <Route path="/strategic-planning/payment-confirmed" element={<GuidedPaymentConfirmedPage product="strategic-planning" />} />
          <Route path="/strategic-planning/welcome" element={<GuidedWelcomePage product="strategic-planning" />} />
          <Route path="/strategic-planning/intake" element={<GuidedIntakePage product="strategic-planning" />} />
          <Route path="/strategic-planning/dashboard" element={<GuidedDashboardPage product="strategic-planning" />} />
          <Route path="/strategic-planning-form/:token" element={<StrategicPlanningFormPage />} />
          <Route path="/community-need-research/:token" element={<CommunityNeedResearchPage />} />
          <Route path="/strategic-planning-response/:participantId" element={<StrategicPlanningResponsePage />} />
          <Route path="/strategic-plan-review/:token" element={<StrategicPlanReviewPage />} />
          <Route path="/area-pack/:token" element={<AreaPackPage />} />
          <Route path="/strategic-plan/:token" element={<PublicStrategicPlanPage />} />
          <Route path="/strategic-draft/:token" element={<PublicStrategicPlanPage endpoint="strategic-draft" />} />
          <Route path="/strategic-action-plan/:token" element={<PublicActionPlanPage />} />
          <Route path="/strategic-leadership-portfolio/:token" element={<StrategicLeadershipPortfolioPage />} />
          <Route path="/blog" element={<BlogPage />} />
          <Route path="/blog/:slug" element={<BlogPostPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </GoogleAuthGate>
      </MemberAuthProvider>
    </BrowserRouter>
  );
}

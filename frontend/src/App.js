import { useEffect, useState } from "react";
import axios from "axios";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import "@/App.css";
import { LandingPage } from "@/components/LandingPage";
import { AssessmentForm } from "@/components/AssessmentForm";
import { ConfirmationScreen } from "@/components/ConfirmationScreen";
import JoinBoardPage from "@/pages/JoinBoardPage";
import AdminPage from "@/pages/AdminPage";
import LegalPage from "@/pages/LegalPage";
import FunnelLandingPage from "@/funnels/FunnelLandingPage";
import FunnelResultPage from "@/funnels/FunnelResultPage";
import FunnelOptionsPage from "@/funnels/FunnelOptionsPage";
import RecruitProcessPage from "@/funnels/RecruitProcessPage";
import RecruitCheckoutPage from "@/funnels/RecruitCheckoutPage";
import RecruitWithRooneyPage from "@/funnels/RecruitWithRooneyPage";
import BoardRecruitmentProposalPage, { BoardRecruitmentProposalConfirmedPage } from "@/funnels/BoardRecruitmentProposalPage";
import AboutRooneyPage from "@/funnels/AboutRooneyPage";
import RecruitYourBoardYourselfPage from "@/funnels/RecruitYourBoardYourselfPage";
import BoardRecruitmentIntakePage from "@/funnels/BoardRecruitmentIntakePage";
import RecruitmentStartHerePage from "@/funnels/RecruitmentStartHerePage";
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
import StrategicPlanningFormPage from "@/funnels/StrategicPlanningFormPage";
import StrategicPlanReviewPage from "@/funnels/StrategicPlanReviewPage";
import AreaPackPage from "@/funnels/AreaPackPage";
import PublicStrategicPlanPage, { PublicActionPlanPage } from "@/funnels/PublicStrategicPlanPage";
import { PAGE_META, usePageMeta } from "@/seo";
import GameHomePage from "@/game/GameHomePage";
import GameAuthPage from "@/game/GameAuthPage";
import GameAuthCallback from "@/game/GameAuthCallback";
import GameProfilePage from "@/game/GameProfilePage";
import GameWelcomePage from "@/game/GameWelcomePage";
import GameSituationPage from "@/game/GameSituationPage";
import GameDashboardPage from "@/game/GameDashboardPage";
import GamePlayPage from "@/game/GamePlayPage";

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
          <Route path="/" element={<GameHomePage />} />
          <Route path="/fundraising-system" element={<HomeExperience />} />
          <Route path="/game/signup" element={<GameAuthPage />} />
          <Route path="/game/start" element={<GameProfilePage />} />
          <Route path="/game/welcome" element={<GameWelcomePage />} />
          <Route path="/game/setup" element={<GameSituationPage />} />
          <Route path="/game/dashboard" element={<GameDashboardPage />} />
          <Route path="/play/:token" element={<GamePlayPage />} />
          <Route path="/board-assessment" element={<LegacyAssessmentPage />} />
          <Route path="/board-transformation" element={<BoardTransformationPage />} />
          <Route path="/board-transformation/result/:token" element={<BoardTransformationResultPage />} />
          <Route path="/activate-with-rooney" element={<ActivateWithRooneyPage />} />
          <Route path="/recruit" element={<FunnelLandingPage offerSource="recruitment" />} />
          <Route path="/board-fix" element={<FunnelLandingPage offerSource="board_fix" />} />
          <Route path="/offer/board-fix" element={<OfferVideoPage offer="board-fix" />} />
          <Route path="/offer/fundraising-board-builder" element={<FundraisingBoardBuilderOfferPage />} />
          <Route path="/welcome" element={<WelcomePage />} />
          <Route path="/board-reactivation" element={<Navigate to="/" replace />} />
          <Route path="/board-recruitment" element={<DirectOfferPage pathway="recruitment" />} />
          <Route path="/board-fundraising-activation" element={<DirectOfferPage pathway="activation" />} />
          <Route path="/complete-board-transformation" element={<Navigate to="/" replace />} />
          <Route path="/board-fix-intake" element={<BoardFixIntakePage />} />
          <Route path="/board-fix-roadmap" element={<BoardFixRoadmapPage />} />
          <Route path="/board-fix-dashboard" element={<BoardFixRoadmapPage />} />
          <Route path="/board-fix-orientation" element={<BoardFixOrientationPage />} />
          <Route path="/recruit/process" element={<RecruitProcessPage />} />
          <Route path="/recruit/checkout" element={<RecruitCheckoutPage />} />
          <Route path="/recruit-with-rooney" element={<RecruitWithRooneyPage />} />
          <Route path="/board-recruitment-proposal" element={<BoardRecruitmentProposalPage />} />
          <Route path="/board-recruitment-proposal/confirmed" element={<BoardRecruitmentProposalConfirmedPage />} />
          <Route path="/about-rooney" element={<AboutRooneyPage />} />
          <Route path="/recruit-your-board-yourself" element={<RecruitYourBoardYourselfPage />} />
          <Route path="/board-recruitment-intake" element={<BoardRecruitmentIntakePage />} />
          <Route path="/recruitment-start-here" element={<RecruitmentStartHerePage />} />
          <Route path="/reactivate" element={<FunnelLandingPage offerSource="reactivation" />} />
          <Route path="/reactivate-with-rooney" element={<ReactivateWithRooneyPage />} />
          <Route path="/reactivate-your-board-yourself" element={<ReactivateYourBoardYourselfPage />} />
          <Route path="/board-reactivation-proposal" element={<BoardReactivationProposalPage />} />
          <Route path="/board-reactivation-intake" element={<BoardReactivationIntakePage />} />
          <Route path="/reactivation-start-here" element={<ReactivationStartHerePage />} />
          <Route path="/board-recommitment/:token" element={<BoardRecommitmentFormPage />} />
          <Route path="/portfolio/:token" element={<PortfolioPage />} />
          <Route path="/app/reactivation/self-guided" element={<ReactivationOverviewPage />} />
          <Route path="/app/reactivation/self-guided/module/:moduleNumber" element={<ReactivationModulePage />} />
          <Route path="/activate" element={<FunnelLandingPage offerSource="fundraising_activation" />} />
          <Route path="/activate-your-board-yourself" element={<ActivateYourBoardYourselfPage />} />
          <Route path="/board-activation-proposal" element={<BoardActivationProposalPage />} />
          <Route path="/board-activation-intake" element={<BoardActivationIntakePage />} />
          <Route path="/activation-start-here" element={<ActivationStartHerePage />} />
          <Route path="/planning-form/:token" element={<PlanningFormPage />} />
          <Route path="/strategy-review/:token" element={<StrategyReviewPage />} />
          <Route path="/strategy-plan/:token" element={<StrategyPlanPage />} />
          <Route path="/offer/recruitment" element={<Navigate to="/board-recruitment" replace />} />
          <Route path="/offer/reactivation" element={<OfferVideoPage offer="reactivation" />} />
          <Route path="/offer/activation" element={<OfferVideoPage offer="activation" />} />
          <Route path="/fundraising-portfolio/:token" element={<FundraisingPortfolioPage />} />
          <Route path="/case-for-support/:token" element={<CaseForSupportPage />} />
          <Route path="/app/activation/self-guided/my-fundraising-board" element={<MyFundraisingBoardPage />} />
          <Route path="/app/activation/start" element={<ActivationStartPage />} />
          <Route path="/app/activation/resources" element={<ActivationResourcesPage />} />
          <Route path="/app/activation/self-guided" element={<ActivationOverviewPage />} />
          <Route path="/app/activation/self-guided/module/:moduleNumber" element={<ActivationModulePage />} />
          <Route path="/reactivate/result/:token" element={<FunnelResultPage offerSource="reactivation" />} />
          <Route path="/activate/result/:token" element={<FunnelResultPage offerSource="fundraising_activation" />} />
          <Route path="/recruit/options" element={<FunnelOptionsPage offerSource="recruitment" />} />
          <Route path="/reactivate/options" element={<FunnelOptionsPage offerSource="reactivation" />} />
          <Route path="/activate/options" element={<FunnelOptionsPage offerSource="fundraising_activation" />} />
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
          <Route path="/strategic-planning-form/:token" element={<StrategicPlanningFormPage />} />
          <Route path="/strategic-plan-review/:token" element={<StrategicPlanReviewPage />} />
          <Route path="/area-pack/:token" element={<AreaPackPage />} />
          <Route path="/strategic-plan/:token" element={<PublicStrategicPlanPage />} />
          <Route path="/strategic-action-plan/:token" element={<PublicActionPlanPage />} />
          <Route path="/blog" element={<BlogPage />} />
          <Route path="/blog/:slug" element={<BlogPostPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </GoogleAuthGate>
      </MemberAuthProvider>
    </BrowserRouter>
  );
}

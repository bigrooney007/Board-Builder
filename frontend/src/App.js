import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "@/App.css";
import { MemberAuthProvider } from "@/member/MemberAuthContext";
import { LoginPage, ForgotPasswordPage, ResetPasswordPage } from "@/member/AuthPages";
import { PurchaseSuccessPage } from "@/member/PurchaseSuccessPage";
import { DashboardPage } from "@/member/DashboardPage";
import BoardRecruitmentPage from "@/member/BoardRecruitmentPage";
import RecruitmentResultsPage from "@/member/workspace/ResultsPage";
import { MaterialsLibraryPage } from "@/member/workspace/MaterialsLibrary";
import SelectionOfferPage from "@/member/SelectionOfferPage";
import GameHomePage from "@/game/GameHomePage";
import GameDashboardPage from "@/game/GameDashboardPage";
import GameSituationPage from "@/game/GameSituationPage";
import GamePlayPage from "@/game/GamePlayPage";
import GroupGamePage from "@/game/GroupGamePage";
import GroupPlayPage from "@/game/GroupPlayPage";
import StrategyPage from "@/game/StrategyPage";
import SharedStrategyPage from "@/game/SharedStrategyPage";
import PriorityReviewPage from "@/game/PriorityReviewPage";
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
import BoardStrategyReviewPage from "@/game/BoardStrategyReviewPage";
import ExecutionMaterialsPage from "@/game/ExecutionMaterialsPage";
import RelationshipMapDashboardPage from "@/game/RelationshipMapDashboardPage";
import RelationshipMappingPage from "@/game/RelationshipMappingPage";
import FinalStrategyMemberPage from "@/game/FinalStrategyMemberPage";
import RecruitFreePage from "@/funnels/RecruitFreePage";
import RecruitWalkthroughPage from "@/funnels/RecruitWalkthroughPage";
import LegalPage from "@/pages/LegalPage";


export default function App() {
  return (
    <BrowserRouter>
      <MemberAuthProvider>
        <Routes>
          <Route path="/" element={<GameHomePage />} />
          <Route path="/play/:token" element={<GamePlayPage />} />
          <Route path="/game/unlock" element={<UnlockGamePage />} />
          <Route path="/game/setup" element={<GameSituationPage />} />
          <Route path="/game/dashboard" element={<GameDashboardPage />} />
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
          <Route path="/game/board-review" element={<BoardStrategyReviewPage />} />
          <Route path="/game/execution-materials" element={<ExecutionMaterialsPage />} />
          <Route path="/game/relationships" element={<RelationshipMapDashboardPage />} />
          <Route path="/game/final/:token" element={<FinalStrategyMemberPage />} />
          <Route path="/relationship-mapping/:token" element={<RelationshipMappingPage />} />
          <Route path="/strategy/:shareToken" element={<SharedStrategyPage />} />

          <Route path="/recruit" element={<RecruitFreePage />} />
          <Route path="/recruit/walkthrough" element={<RecruitWalkthroughPage />} />

          <Route path="/purchase/success" element={<PurchaseSuccessPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
          <Route path="/app" element={<DashboardPage />} />
          <Route path="/app/board-recruitment" element={<BoardRecruitmentPage />} />
          <Route path="/app/recruitment/self-guided/results" element={<RecruitmentResultsPage />} />
          <Route path="/app/recruitment/self-guided/materials" element={<MaterialsLibraryPage />} />
          <Route path="/app/recruitment/selection-offer" element={<SelectionOfferPage />} />

          <Route path="/privacy-policy" element={<LegalPage type="privacy" />} />
          <Route path="/terms" element={<LegalPage type="terms" />} />

          <Route path="/game/signup" element={<Navigate to="/" replace />} />
          <Route path="/game/start" element={<Navigate to="/" replace />} />
          <Route path="/game/welcome" element={<Navigate to="/" replace />} />
          <Route path="/game/upgrade" element={<Navigate to="/game/unlock" replace />} />
          <Route path="/recruit/checkout" element={<Navigate to="/recruit/walkthrough" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </MemberAuthProvider>
    </BrowserRouter>
  );
}

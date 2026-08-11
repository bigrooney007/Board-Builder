import { useState } from "react";
import { BrowserRouter, Route, Routes, useNavigate } from "react-router-dom";
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
import { MemberAuthProvider } from "@/member/MemberAuthContext";
import { LoginPage, ForgotPasswordPage, ResetPasswordPage } from "@/member/AuthPages";
import { PurchaseSuccessPage } from "@/member/PurchaseSuccessPage";
import { DashboardPage } from "@/member/DashboardPage";
import { CourseOverviewPage, CourseModulePage } from "@/member/CoursePages";
import { MaterialsLibraryPage } from "@/member/workspace/MaterialsLibrary";
import RecruitmentResultsPage from "@/member/workspace/ResultsPage";
import { OpportunityApplyPage, SavedProfileApplyPage, SignAgreementPage } from "@/public/OpportunityPages";
import { BlogPage, BlogPostPage } from "@/pages/BlogPages";
import { SharedResourcePage, BoardProfileFormPage } from "@/pages/SharedPages";
import CandidateReferenceFormPage, { RefereeFormPage } from "@/public/ReferencePages";
import { ReviewProgressTracker } from "@/reviewMode";
import { PAGE_META, usePageMeta } from "@/seo";

const HomeExperience = () => {
  usePageMeta(...PAGE_META.home);
  const navigate = useNavigate();
  return <LandingPage onJoin={() => navigate("/join-a-board")} />;
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
        <ReviewProgressTracker />
        <Routes>
          <Route path="/" element={<HomeExperience />} />
          <Route path="/board-assessment" element={<LegacyAssessmentPage />} />
          <Route path="/recruit" element={<FunnelLandingPage offerSource="recruitment" />} />
          <Route path="/recruit/process" element={<RecruitProcessPage />} />
          <Route path="/recruit/checkout" element={<RecruitCheckoutPage />} />
          <Route path="/recruit-with-rooney" element={<RecruitWithRooneyPage />} />
          <Route path="/reactivate" element={<FunnelLandingPage offerSource="reactivation" />} />
          <Route path="/activate" element={<FunnelLandingPage offerSource="fundraising_activation" />} />
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
          <Route path="/board-opportunities/:slug/apply" element={<OpportunityApplyPage />} />
          <Route path="/apply/:token" element={<SavedProfileApplyPage />} />
          <Route path="/sign/:token" element={<SignAgreementPage />} />
          <Route path="/shared/:token" element={<SharedResourcePage />} />
          <Route path="/board-profile/:token" element={<BoardProfileFormPage />} />
          <Route path="/reference-form/:token" element={<CandidateReferenceFormPage />} />
          <Route path="/referee-form/:token" element={<RefereeFormPage />} />
          <Route path="/blog" element={<BlogPage />} />
          <Route path="/blog/:slug" element={<BlogPostPage />} />
        </Routes>
      </MemberAuthProvider>
    </BrowserRouter>
  );
}

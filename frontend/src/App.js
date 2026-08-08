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

const HomeExperience = () => {
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
  return <BrowserRouter><Routes><Route path="/" element={<HomeExperience />} /><Route path="/board-assessment" element={<LegacyAssessmentPage />} /><Route path="/recruit" element={<FunnelLandingPage offerSource="recruitment" />} /><Route path="/reactivate" element={<FunnelLandingPage offerSource="reactivation" />} /><Route path="/activate" element={<FunnelLandingPage offerSource="fundraising_activation" />} /><Route path="/recruit/result/:token" element={<FunnelResultPage offerSource="recruitment" />} /><Route path="/reactivate/result/:token" element={<FunnelResultPage offerSource="reactivation" />} /><Route path="/activate/result/:token" element={<FunnelResultPage offerSource="fundraising_activation" />} /><Route path="/recruit/options" element={<FunnelOptionsPage offerSource="recruitment" />} /><Route path="/reactivate/options" element={<FunnelOptionsPage offerSource="reactivation" />} /><Route path="/activate/options" element={<FunnelOptionsPage offerSource="fundraising_activation" />} /><Route path="/join-a-board" element={<JoinBoardPage />} /><Route path="/privacy-policy" element={<LegalPage type="privacy" />} /><Route path="/terms" element={<LegalPage type="terms" />} /><Route path="/admin" element={<AdminPage />} /></Routes></BrowserRouter>;
}
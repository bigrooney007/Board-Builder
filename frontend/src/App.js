import { useState } from "react";
import { BrowserRouter, Route, Routes, useNavigate } from "react-router-dom";
import "@/App.css";
import { LandingPage } from "@/components/LandingPage";
import { AssessmentForm } from "@/components/AssessmentForm";
import { ConfirmationScreen } from "@/components/ConfirmationScreen";
import JoinBoardPage from "@/pages/JoinBoardPage";
import AdminPage from "@/pages/AdminPage";
import LegalPage from "@/pages/LegalPage";
import TrackedActionPage from "@/pages/TrackedActionPage";

const HomeExperience = () => {
  const [view, setView] = useState("home");
  const [confirmation, setConfirmation] = useState(null);
  const navigate = useNavigate();
  const startAssessment = () => { setView("assessment"); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const returnHome = () => { setConfirmation(null); setView("home"); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const completeAssessment = (result) => { setConfirmation(result); setView("confirmation"); window.scrollTo({ top: 0, behavior: "smooth" }); };
  if (view === "assessment") return <AssessmentForm onComplete={completeAssessment} onHome={returnHome} />;
  if (view === "confirmation") return <ConfirmationScreen confirmation={confirmation} onHome={returnHome} />;
  return <LandingPage onStart={startAssessment} onJoin={() => navigate("/join-a-board")} />;
};

export default function App() {
  return <BrowserRouter><Routes><Route path="/" element={<HomeExperience />} /><Route path="/join-a-board" element={<JoinBoardPage />} /><Route path="/privacy-policy" element={<LegalPage type="privacy" />} /><Route path="/terms" element={<LegalPage type="terms" />} /><Route path="/board-transformation-ready" element={<TrackedActionPage type="board-transformation-ready" />} /><Route path="/available-to-serve" element={<TrackedActionPage type="available-to-serve" />} /><Route path="/admin" element={<AdminPage />} /></Routes></BrowserRouter>;
}
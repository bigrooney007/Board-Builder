import { useState } from "react";
import "@/App.css";
import { LandingPage } from "@/components/LandingPage";
import { AssessmentForm } from "@/components/AssessmentForm";
import { ConfirmationScreen } from "@/components/ConfirmationScreen";

export default function App() {
  const [view, setView] = useState("home");
  const [confirmation, setConfirmation] = useState(null);

  const startAssessment = () => {
    setView("assessment");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const returnHome = () => {
    setConfirmation(null);
    setView("home");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const completeAssessment = (result) => {
    setConfirmation(result);
    setView("confirmation");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (view === "assessment") {
    return <AssessmentForm onComplete={completeAssessment} onHome={returnHome} />;
  }
  if (view === "confirmation") {
    return <ConfirmationScreen confirmation={confirmation} onHome={returnHome} />;
  }
  return <LandingPage onStart={startAssessment} />;
}
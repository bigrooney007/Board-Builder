import React from "react";
import { memberApi } from "../api";
import { MaterialCard } from "./MaterialCard";
import { useMaterials } from "./WorkspaceModules";
import { recruitmentContent, module1ProfileText } from "../../content/appContent";

export const Module1Profile = ({ onConfirmed }) => {
  const { byType, refresh } = useMaterials();
  const saveAndConfirm = async () => {
    const assessment = (await memberApi.get("/recruit/free/member-assessment/current")).data;
    const answers = assessment?.answers || {};
    const required = ["mission", "current_board", "important_areas", "support_needs"];
    if (required.some((key) => !String(answers[key] || "").trim())) throw new Error("Complete all four Board Recruitment Game questions first.");

    await memberApi.post(`/recruit/free/${assessment.token}/result`);
    await memberApi.post("/workspace/profile/confirm");
    await refresh();
    if (onConfirmed) onConfirmed();

    // The result endpoint creates the Board Member profiles from the exact four
    // Recruitment Game answers, so do not trigger a second AI generation.
    return false;
  };

  return (
    <div data-testid="module1-workspace">
      <section className="workspace-panel" data-testid="module1-intake">
        <h2>{module1ProfileText.theBoardMembersYourOrganization}</h2>
        <p className="material-description">{module1ProfileText.basedOnTheInformationYou}</p>
        <p className="workspace-note">No additional form is required. This result uses the organization name and recruitment number supplied at the beginning, together with all four Recruitment Game answers and the present-board information you confirmed.</p>
        <MaterialCard
          type="powerhouse_board_blueprint"
          title={module1ProfileText.theBoardMembersYourOrganization2}
          buttonLabel={recruitmentContent.module2.generateBoardButton}
          description="One exact profile for each new board member you want to recruit — who they are, why they matter to your organization and what to look for. Read it, edit anything you want changed, then approve it. The approved result is used automatically throughout your recruitment campaign."
          material={byType.powerhouse_board_blueprint}
          refresh={refresh}
          beforeGenerate={saveAndConfirm}
          approvable
        />
      </section>
    </div>
  );
};

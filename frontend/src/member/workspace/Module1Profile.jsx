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
    const required = ["mission", "current_board", "desired_board_members", "support_needs", "board_type", "why_join"];
    if (required.some((key) => !String(answers[key] || "").trim())) throw new Error("Complete all six Recruitment Questions first.");

    await memberApi.post(`/recruit/free/${assessment.token}/result`);
    await memberApi.post("/workspace/profile/confirm");
    await refresh();
    if (onConfirmed) onConfirmed();

    // The result endpoint uses the six Recruitment Questions and the saved recruitment target, so do not trigger a second duplicate generation.
    return false;
  };

  return (
    <div data-testid="module1-workspace">
      <section className="workspace-panel" data-testid="module1-intake">
        <h2>{module1ProfileText.theBoardMembersYourOrganization}</h2>
        <p className="material-description">{module1ProfileText.basedOnTheInformationYou}</p>
        <p className="workspace-note">No additional form is required. This result uses the organization name and recruitment number supplied at the beginning, together with all six Recruitment Questions, the present board you described and the kind of board you want to build.</p>
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

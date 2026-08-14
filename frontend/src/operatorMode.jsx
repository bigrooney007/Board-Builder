import { useMemberAuth } from "@/member/MemberAuthContext";

export const enterOperatorMode = (userId, organization, product) => {
  sessionStorage.setItem("operateAsUserId", userId);
  sessionStorage.setItem("operateAsOrg", organization || "Client Organization");
  sessionStorage.setItem("operateAsProduct", product || "");
};

export const exitOperatorMode = () => {
  sessionStorage.removeItem("operateAsUserId");
  sessionStorage.removeItem("operateAsOrg");
  sessionStorage.removeItem("operateAsProduct");
};

export const WorkspaceModeBanner = () => {
  const { member } = useMemberAuth() || {};
  const operateAs = sessionStorage.getItem("operateAsUserId");
  if (operateAs) {
    return (
      <div className="review-mode-banner" data-testid="operator-mode-banner" style={{ background: "#0b3d2e", color: "#fff", padding: "8px 16px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        <span>OPERATING CLIENT WORKSPACE — {sessionStorage.getItem("operateAsOrg")} ({sessionStorage.getItem("operateAsProduct")})</span>
        <button className="button button-small" data-testid="exit-operator-mode" onClick={() => { exitOperatorMode(); window.location.href = "/admin"; }}>Exit Client Workspace</button>
      </div>
    );
  }
  if (member?.review_mode) {
    return (
      <div className="review-mode-banner" data-testid="admin-test-mode-banner" style={{ background: "#8a5a00", color: "#fff", padding: "8px 16px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        <span>TEST MODE — Admin Product Journey (isolated test workspace, no emails are sent automatically, no real client data is affected)</span>
        <a className="button button-small" href="/admin" data-testid="test-mode-back-to-admin">Back to Admin</a>
      </div>
    );
  }
  return null;
};

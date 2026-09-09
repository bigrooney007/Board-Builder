import axios from "axios";

export const getAdminPreview = () => {
  try { return JSON.parse(sessionStorage.getItem("adminPreview")) || null; } catch { return null; }
};
export const setAdminPreview = (preview) => sessionStorage.setItem("adminPreview", JSON.stringify(preview));
export const clearAdminPreview = () => sessionStorage.removeItem("adminPreview");

export const previewHeaders = () => {
  const preview = getAdminPreview();
  if (!preview) return {};
  if (preview.mode === "customer" && preview.memberId) return { "X-Admin-Preview-Member": preview.memberId };
  return { "X-Admin-Preview": "fresh" };
};

axios.interceptors.request.use((config) => {
  Object.assign(config.headers, previewHeaders());
  return config;
});

export const AdminPreviewBanner = () => {
  const preview = getAdminPreview();
  if (!preview) return null;
  const label = preview.mode === "customer"
    ? `Viewing as customer: ${preview.name || preview.memberId} (read-only)`
    : "Fresh Customer View";
  return (
    <div className="review-mode-banner" data-testid="admin-preview-banner">
      ADMIN PREVIEW — {label}
      <button
        className="button button-small"
        data-testid="admin-preview-exit"
        style={{ marginLeft: 14 }}
        onClick={() => { clearAdminPreview(); window.location.assign("/admin"); }}
      >
        EXIT PREVIEW
      </button>
    </div>
  );
};

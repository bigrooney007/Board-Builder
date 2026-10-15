import { useEffect, useState } from "react";
import { Route, Routes, useLocation, useNavigate } from "react-router-dom";
import V2Shell, { ErrorNotice, Loading, PreviewGate } from "./V2Shell";
import PaidSetupPage from "./PaidSetupPage";
import AdminPaidTestPage from "./AdminPaidTestPage";
import { errorMessage, v2Api } from "./api";
import { FreeIntakePage, MarketplacePage, NotFoundPage, OfferPage, PaymentPage, ProductIndexPage, ProductLandingPage, RecoveryPage } from "./PublicPages";
import { CampaignPage, InvitationsPage, ResourceEditorPage, ResourceLibraryPage, ResourcesPage, ResponsePage, ResponsesPage } from "./ResourcePages";
import { GroupPage, SharedMeetingPage } from "./GroupPages";
import { ParticipantPage } from "./ParticipantPages";

// React StrictMode can replay an effect before the first request finishes.
// Exchange a one-use email token once and let both effect instances await it.
const accessExchanges = new Map();
const exchangeOnce = (token) => {
  if (!accessExchanges.has(token)) {
    const pending = v2Api.post("/access-link", { token }).catch((error) => {
      accessExchanges.delete(token);
      throw error;
    });
    accessExchanges.set(token, pending);
  }
  return accessExchanges.get(token);
};

export const safeV2Path = (path) => {
  if (!path || !path.startsWith("/v2/") || /[\\\r\n]/.test(path)) return "";
  try {
    const url = new URL(path, window.location.origin);
    let decoded = url.pathname;
    for (let i = 0; i < 5; i += 1) { const next = decodeURIComponent(decoded); if (next === decoded) break; decoded = next; }
    if (url.origin !== window.location.origin || !decoded.startsWith("/v2/") || decoded.includes("//") || /[\\\r\n]/.test(decoded)
      || decoded.split("/").some((segment) => segment === "." || segment === "..") || url.searchParams.has("access") || url.searchParams.has("token")) return "";
    return `${url.pathname}${url.search}${url.hash}`;
  } catch { return ""; }
};

function SecureLinkExchange({ children }) {
  const location = useLocation(); const navigate = useNavigate();
  const params = new URLSearchParams(location.search);
  const token = params.get("access") || (location.pathname === "/v2/access" ? params.get("token") : "") || "";
  const [error, setError] = useState(""); const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!token) return undefined;
    let active = true; setError("");
    const clean = new URLSearchParams(location.search); clean.delete("access"); clean.delete("token"); clean.delete("next");
    const cleanPath = `${location.pathname}${clean.size ? `?${clean.toString()}` : ""}${location.hash}`;
    // Remove the bearer link from browser history before any resource is requested.
    window.history.replaceState(window.history.state, "", cleanPath);
    exchangeOnce(token).then(({ data }) => {
      if (!active) return;
      const preferred = safeV2Path(new URLSearchParams(location.search).get("next"));
      navigate(preferred || (location.pathname === "/v2/access" ? `/v2/resources/${encodeURIComponent(data.journey_id)}` : cleanPath), { replace: true });
    }).catch((err) => { if (active) setError(errorMessage(err, "This secure link may have expired. Recover your access to receive a new link.")); });
    return () => { active = false; };
  }, [token, location.pathname, location.search, location.hash, navigate, attempt]);
  if (!token) return children;
  return <V2Shell title="Opening your secure link" narrow>{error ? <section className="v2-card"><h1>We could not open your secure link.</h1><ErrorNotice error={error} /><div className="v2-actions"><button className="v2-button" onClick={() => setAttempt((n) => n + 1)}>Try again</button><button className="v2-button v2-button-secondary" onClick={() => navigate("/v2/recover", { replace: true })}>Recover my resources</button></div></section> : <Loading>Verifying your secure link…</Loading>}</V2Shell>;
}

const protectedPage = (page) => <PreviewGate>{page}</PreviewGate>;
export default function V2Routes() {
  return <SecureLinkExchange><Routes>
    <Route index element={protectedPage(<ProductIndexPage />)} />
    <Route path="admin-test/marketplace" element={protectedPage(<MarketplacePage endpoint="/admin/test-api/marketplace" />)} />
    <Route path="admin-test/:product" element={protectedPage(<AdminPaidTestPage />)} />
    <Route path="recover" element={<RecoveryPage />} />
    <Route path="access" element={<NotFoundPage />} />
    <Route path="forms/:token" element={<ParticipantPage />} />
    <Route path="meeting/:token" element={<SharedMeetingPage />} />
    <Route path="marketplace" element={protectedPage(<MarketplacePage />)} />
    <Route path="setup/:journeyId" element={protectedPage(<PaidSetupPage />)} />
    <Route path="library/:journeyId" element={protectedPage(<ResourceLibraryPage />)} />
    <Route path="resources/:journeyId" element={protectedPage(<ResourcesPage />)} />
    <Route path="resources/:journeyId/:resourceId" element={protectedPage(<ResourceEditorPage />)} />
    <Route path="responses/:journeyId" element={protectedPage(<ResponsesPage />)} />
    <Route path="responses/:journeyId/:submissionId" element={protectedPage(<ResponsePage />)} />
    <Route path="invite/:journeyId" element={protectedPage(<InvitationsPage />)} />
    <Route path="group/:journeyId" element={protectedPage(<GroupPage />)} />
    <Route path="campaign/:journeyId" element={protectedPage(<CampaignPage />)} />
    <Route path=":product/start" element={protectedPage(<FreeIntakePage />)} />
    <Route path=":product/offer" element={protectedPage(<OfferPage />)} />
    <Route path=":product/payment" element={protectedPage(<PaymentPage />)} />
    <Route path=":product/resources/:journeyId" element={protectedPage(<ResourcesPage />)} />
    <Route path=":product" element={protectedPage(<ProductLandingPage />)} />
    <Route path="*" element={<NotFoundPage />} />
  </Routes></SecureLinkExchange>;
}

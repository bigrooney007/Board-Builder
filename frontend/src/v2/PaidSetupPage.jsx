import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import V2Shell, { ErrorNotice, Loading } from "./V2Shell";
import { errorMessage, v2Api } from "./api";
import { PRODUCTS } from "./content";

export default function PaidSetupPage() {
  const { journeyId } = useParams();
  const navigate = useNavigate();
  const [journey, setJourney] = useState(null);
  const [branding, setBranding] = useState({ organization_name: "", logo_data: "", primary_color: "", secondary_color: "" });
  const [meeting, setMeeting] = useState({ date: "", time: "", timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/London" });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    v2Api.get(`/journeys/${journeyId}`).then(({ data }) => {
      if (!active) return;
      if (data.state !== "paid") throw new Error("Complete your purchase before confirming these details.");
      if (data.setup_complete && data.setup_initialization_status === "complete") { navigate(`/v2/resources/${journeyId}`, { replace: true }); return; }
      setJourney(data);
      setBranding((old) => ({ ...old, ...data.branding, organization_name: data.branding?.organization_name || data.organization }));
      if (data.meeting) setMeeting((old) => ({ ...old, ...data.meeting }));
    }).catch((problem) => { if (active) setError(errorMessage(problem, problem.message)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [journeyId, navigate]);
  const groupProduct = ["board-fundraising-game", "strategic-planning"].includes(journey?.product);
  const upload = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 1024 * 1024) { setError("Choose a PNG, JPEG or WebP logo smaller than 1 MB."); event.target.value = ""; return; }
    const reader = new FileReader();
    reader.onload = () => { setBranding((old) => ({ ...old, logo_data: reader.result })); setError(""); };
    reader.onerror = () => setError("We could not read that logo. Please choose it again.");
    reader.readAsDataURL(file);
  };
  const save = async (event) => {
    event.preventDefault(); if (busy) return;
    if ([branding.primary_color, branding.secondary_color].some((color) => color && !/^#[0-9a-f]{6}$/i.test(color))) { setError("Enter optional colors in six-digit hex format, such as #243B64, or leave them blank."); return; }
    setBusy(true); setError("");
    try {
      await v2Api.post(`/journeys/${journeyId}/setup`, { branding, ...(groupProduct ? { meeting } : {}) });
      navigate(`/v2/resources/${journeyId}`, { replace: true });
    } catch (problem) { setError(errorMessage(problem, "Your payment is saved. Please check these details and try again.")); }
    finally { setBusy(false); }
  };
  return <V2Shell title="Prepare your purchased resources" narrow>
    {loading ? <Loading>Opening your purchase…</Loading> : <form className="v2-card" onSubmit={save}>
      <p className="v2-eyebrow">YOUR PAYMENT IS CONFIRMED</p><h1>Prepare your {PRODUCTS[journey?.product]?.name || "board"} resources.</h1>
      <p>Confirm your organization details now so we can use them on your forms and documents. Your logo and colors are optional. Leave them blank for a neutral professional design.</p>
      {journey && <>
        <label>Organization name<input required maxLength={200} value={branding.organization_name} onChange={(event) => setBranding({ ...branding, organization_name: event.target.value })} /></label>
        <label>Organization logo, optional<input type="file" accept="image/png,image/jpeg,image/webp" onChange={upload} /><small>PNG, JPEG or WebP, up to 1 MB.</small></label>
        {branding.logo_data && <div className="v2-logo-preview"><img src={branding.logo_data} alt="Your organization logo" /><button type="button" className="v2-text-button" onClick={() => setBranding({ ...branding, logo_data: "" })}>Remove logo</button></div>}
        <div className="v2-branding-fields"><label>Primary brand color, optional<input placeholder="#243B64" maxLength={7} value={branding.primary_color} onChange={(event) => setBranding({ ...branding, primary_color: event.target.value })} /></label><label>Secondary brand color, optional<input placeholder="#6366F1" maxLength={7} value={branding.secondary_color} onChange={(event) => setBranding({ ...branding, secondary_color: event.target.value })} /></label></div>
        {groupProduct && <section><h2>When is your next board meeting?</h2><p>Set the date and time before inviting people. Your group session will remain available whenever you need to prepare.</p><label>Meeting date<input type="date" required value={meeting.date} onChange={(event) => setMeeting({ ...meeting, date: event.target.value })} /></label><label>Meeting time<input type="time" required value={meeting.time} onChange={(event) => setMeeting({ ...meeting, time: event.target.value })} /></label><label>Time zone<input required value={meeting.timezone} onChange={(event) => setMeeting({ ...meeting, timezone: event.target.value })} /></label></section>}
        {journey.product === "recruit" && <p>Your next step is to review and approve the board member profiles. We will prepare your recruitment pack using the profiles you approve.</p>}
      </>}
      <ErrorNotice error={error} />{journey && <button className="v2-button" disabled={busy}>{busy ? "Saving your details…" : journey.product === "recruit" ? "Save and prepare my board member profiles" : "Save and open my resources"}</button>}
    </form>}
  </V2Shell>;
}

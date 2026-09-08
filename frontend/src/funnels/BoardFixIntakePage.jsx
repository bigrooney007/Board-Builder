import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { FunnelLayout } from "@/funnels/FunnelLayout";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SECTIONS = [
  { heading: "Your Organization", fields: [
    { name: "organization_name", label: "Organization name", type: "text" },
    { name: "website", label: "Website", type: "text", required: false },
    { name: "mission", label: "Mission statement", type: "textarea" },
    { name: "organizational_goals", label: "Organizational goals", type: "textarea" },
    { name: "strategic_priorities", label: "Strategic priorities", type: "textarea" },
  ]},
  { heading: "Your Current Board", fields: [
    { name: "board_size", label: "How many board members do you currently have?", type: "text" },
    { name: "board_members", label: "List your current board members and their roles", type: "textarea" },
    { name: "board_structure", label: "Describe your board structure (officers, committees, terms)", type: "textarea", required: false },
    { name: "board_responsibilities", label: "What responsibilities does your board currently hold?", type: "textarea", required: false },
    { name: "board_engagement", label: "Describe your board members' current engagement", type: "textarea" },
    { name: "board_problems", label: "What are the current problems with your board?", type: "textarea" },
    { name: "contributing_areas", label: "Areas where board members are currently contributing", type: "textarea", required: false },
    { name: "not_contributing_areas", label: "Areas where board members are not contributing", type: "textarea", required: false },
  ]},
  { heading: "Skills, Relationships and Capabilities", fields: [
    { name: "skills_represented", label: "Skills currently represented on the board", type: "textarea", required: false },
    { name: "skills_missing", label: "Skills missing from the board", type: "textarea" },
    { name: "relationships_needed", label: "Relationships and networks your organization needs", type: "textarea", required: false },
    { name: "organizational_capabilities_needed", label: "Organizational capabilities your organization needs", type: "textarea", required: false },
    { name: "recruitment_needs", label: "Your board recruitment needs", type: "textarea", required: false },
  ]},
  { heading: "Fundraising", fields: [
    { name: "fundraising_situation", label: "Describe your current fundraising situation", type: "textarea" },
    { name: "fundraising_capacity_needed", label: "Fundraising capacity your board needs", type: "textarea", required: false },
  ]},
  { heading: "What You Want to Accomplish", fields: [
    { name: "board_accomplish", label: "What do you want your board to accomplish?", type: "textarea" },
    { name: "transformation_areas", label: "The areas where your board currently needs transformation", type: "textarea" },
  ]},
];

export default function BoardFixIntakePage() {
  const navigate = useNavigate();
  const sessionId = new URLSearchParams(window.location.search).get("session_id") || "";
  const [state, setState] = useState("loading");
  const [data, setData] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [bylawsFile, setBylawsFile] = useState(null);
  const [existingBylaws, setExistingBylaws] = useState("");
  const [purchaseSource, setPurchaseSource] = useState("");
  const [contact, setContact] = useState({ name: "", email: "" });
  const isFbb = purchaseSource === "fundraising_board_builder_497";

  useEffect(() => { document.title = "Complete Board Fix Intake | Nonprofit Board Builder"; }, []);

  useEffect(() => {
    axios.get(`${API}/board-fix-intake/context`, { params: sessionId ? { session_id: sessionId } : {}, withCredentials: true })
      .then((r) => {
        setState(r.data.eligible ? "ready" : "blocked");
        setData(r.data.data || {});
        setExistingBylaws(r.data.bylaws_filename || "");
        setPurchaseSource(r.data.purchase_source || "");
        if (r.data.contact_prefill) setContact({ name: r.data.contact_prefill.name || "", email: r.data.contact_prefill.email || "" });
      })
      .catch((err) => {
        if (!sessionId && err.response?.status === 401) {
          window.location.replace(`/login?next=${encodeURIComponent("/board-fix-intake")}`);
          return;
        }
        setState("blocked");
      });
  }, [sessionId]);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    const missing = SECTIONS.flatMap((s) => s.fields).filter((f) => f.required !== false && !(data[f.name] || "").trim());
    if (missing.length) { setError(`Please complete: ${missing.map((f) => f.label).join("; ")}`); return; }
    if (isFbb && (!contact.name.trim() || !contact.email.trim())) { setError("Enter your name and email so we can create your customer account."); return; }
    setBusy(true);
    try {
      const response = await axios.post(`${API}/board-fix-intake/submit`, {
        session_id: sessionId, data,
        contact_name: contact.name, contact_email: contact.email, origin_url: window.location.origin,
      }, { withCredentials: true });
      if (bylawsFile) {
        try {
          const upload = new FormData();
          upload.append("session_id", sessionId);
          upload.append("file", bylawsFile);
          await axios.post(`${API}/board-fix-intake/bylaws`, upload, { withCredentials: true });
        } catch { /* bylaws are optional — never block completion */ }
      }
      const destination = response.data.redirect_url || "/board-fix-roadmap";
      if (destination === "/app") { window.location.href = "/app"; return; }
      if (destination.startsWith("http")) { window.location.href = destination; return; }
      navigate(destination);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = typeof detail === "string"
        ? detail
        : Array.isArray(detail) ? detail.map((item) => item?.msg || "").filter(Boolean).join(" ") : "";
      setError(message || "We could not save your intake. Please try again.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main className="funnel-page" data-testid="board-fix-intake-page">
        <header className="funnel-hero-banner">
          <p className="eyebrow">{isFbb ? "Fundraising Board Builder" : "Complete Board Fix"}</p>
          <h1 data-testid="board-fix-intake-headline">{isFbb ? "Tell Us About Your Organization" : "Tell Us Everything About Your Board"}</h1>
          <p>{isFbb ? "This information personalizes the tools, documents and materials you will use throughout the process. You will not have to enter it again." : "This information personalizes your entire Complete Board Fix experience. You will not have to enter it again."}</p>
        </header>
        {state === "loading" && <p data-testid="board-fix-intake-loading">{sessionId ? "Please wait while we verify your payment with Stripe." : "Please wait while we verify your Complete Board Fix access."}</p>}
        {state === "blocked" && (
          <section className="member-card" data-testid="board-fix-intake-blocked">
            <p>We could not find a completed Complete Board Fix purchase. If you just paid, please use the link Stripe returned you to.</p>
            <a className="button" href="/offer/board-fix" data-testid="board-fix-intake-blocked-link">Get the Complete Board Fix System</a>
          </section>
        )}
        {state === "ready" && (
          <form className="intake-form" onSubmit={submit} data-testid="board-fix-intake-form">
            {isFbb && (
              <section className="member-card" data-testid="fbb-contact-section">
                <h2>Your Contact Information</h2>
                <p>We will use this to create your customer account and email you your login details.</p>
                <label className="intake-field">Your name
                  <input value={contact.name} onChange={(e) => setContact({ ...contact, name: e.target.value })} data-testid="fbb-contact-name" />
                </label>
                <label className="intake-field">Email address
                  <input type="email" value={contact.email} onChange={(e) => setContact({ ...contact, email: e.target.value })} data-testid="fbb-contact-email" />
                </label>
              </section>
            )}
            {SECTIONS.map((section) => (
              <section className="member-card" key={section.heading}>
                <h2>{section.heading}</h2>
                {section.fields.map((field) => (
                  <label key={field.name} className="intake-field">
                    {field.label}{field.required === false ? " (optional)" : ""}
                    {field.type === "text"
                      ? <input value={data[field.name] || ""} onChange={(e) => setData({ ...data, [field.name]: e.target.value })} data-testid={`board-fix-field-${field.name}`} />
                      : <textarea rows="3" value={data[field.name] || ""} onChange={(e) => setData({ ...data, [field.name]: e.target.value })} data-testid={`board-fix-field-${field.name}`} />}
                  </label>
                ))}
              </section>
            ))}
            <section className="member-card" data-testid="board-fix-bylaws-section">
              <h2>Upload Your Organization's Bylaws (Optional)</h2>
              <p><strong>If you have a copy of your organization's bylaws, you can upload it here. This is optional.</strong></p>
              {existingBylaws && !bylawsFile && (
                <p data-testid="board-fix-bylaws-existing">Currently on file: <strong>{existingBylaws}</strong> — choose a new file below to replace it.</p>
              )}
              <input key={bylawsFile ? "chosen" : "empty"} type="file" accept=".pdf,.doc,.docx"
                onChange={(e) => setBylawsFile(e.target.files?.[0] || null)} data-testid="board-fix-bylaws-input" />
              {bylawsFile && (
                <p data-testid="board-fix-bylaws-selected">Selected: <strong>{bylawsFile.name}</strong>{" "}
                  <button type="button" className="button button-outline" onClick={() => setBylawsFile(null)} data-testid="board-fix-bylaws-clear">Remove</button>
                </p>
              )}
            </section>
            {error && <p className="submit-error" data-testid="board-fix-intake-error">{error}</p>}
            <button className="button" type="submit" disabled={busy} data-testid="board-fix-intake-submit">{busy ? "Saving…" : isFbb ? "Complete My Intake" : "Save and Continue to My Board Fix Roadmap"}</button>
          </form>
        )}
      </main>
    </FunnelLayout>
  );
}

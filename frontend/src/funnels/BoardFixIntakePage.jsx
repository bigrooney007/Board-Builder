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

  useEffect(() => { document.title = "Complete Board Fix Intake | Nonprofit Board Builder"; }, []);

  useEffect(() => {
    axios.get(`${API}/board-fix-intake/context`, { params: { session_id: sessionId } })
      .then((r) => { setState(r.data.eligible ? "ready" : "blocked"); setData(r.data.data || {}); })
      .catch(() => setState("blocked"));
  }, [sessionId]);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    const missing = SECTIONS.flatMap((s) => s.fields).filter((f) => f.required !== false && !(data[f.name] || "").trim());
    if (missing.length) { setError(`Please complete: ${missing.map((f) => f.label).join("; ")}`); return; }
    setBusy(true);
    try {
      const response = await axios.post(`${API}/board-fix-intake/submit`, { session_id: sessionId, data });
      const destination = response.data.redirect_url || "/board-fix-roadmap";
      if (destination.startsWith("http")) { window.location.href = destination; return; }
      navigate(destination);
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your intake. Please try again.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main className="funnel-page" data-testid="board-fix-intake-page">
        <header className="funnel-hero-banner">
          <p className="eyebrow">Complete Board Fix</p>
          <h1 data-testid="board-fix-intake-headline">Tell Us Everything About Your Board</h1>
          <p>This information personalizes your entire Complete Board Fix experience. You will not have to enter it again.</p>
        </header>
        {state === "loading" && <p data-testid="board-fix-intake-loading">Please wait while we verify your payment with Stripe.</p>}
        {state === "blocked" && (
          <section className="member-card" data-testid="board-fix-intake-blocked">
            <p>We could not find a completed Complete Board Fix purchase. If you just paid, please use the link Stripe returned you to.</p>
            <a className="button" href="/offer/board-fix" data-testid="board-fix-intake-blocked-link">Get the Complete Board Fix System</a>
          </section>
        )}
        {state === "ready" && (
          <form className="intake-form" onSubmit={submit} data-testid="board-fix-intake-form">
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
            {error && <p className="submit-error" data-testid="board-fix-intake-error">{error}</p>}
            <button className="button" type="submit" disabled={busy} data-testid="board-fix-intake-submit">{busy ? "Saving…" : "Save and Continue to My Board Fix Roadmap"}</button>
          </form>
        )}
      </main>
    </FunnelLayout>
  );
}

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "./gameShared";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EMPTY = {
  funder_type: "Individual", name: "", organization: "", email: "", phone: "", other_contact: "",
  how_know: "", why_match: "", willing_intro: false, willing_participate: false, willing_ask: false, willing_org_ask: false,
};

const WILLING = [
  ["willing_intro", "Make An Introduction"],
  ["willing_participate", "Participate In The Ask"],
  ["willing_ask", "Make The Ask Myself"],
  ["willing_org_ask", "Have The Organization Make The Ask After My Introduction"],
];

export default function RelationshipMappingPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [invalid, setInvalid] = useState(false);

  useEffect(() => { document.title = "Relationship Mapping | Board Fundraising Game"; }, []);
  useEffect(() => {
    axios.get(`${API}/game/play/${token}/relationships`)
      .then((response) => setData(response.data))
      .catch(() => setInvalid(true));
  }, [token]);

  if (invalid) {
    return (
      <BfgShell>
        <main className="bfg-flow" style={{ textAlign: "center" }}>
          <p className="bfg-error" style={{ marginTop: 40 }}>This link is not valid.</p>
        </main>
      </BfgShell>
    );
  }
  if (!data) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  const toggle = (key) => () => setForm({ ...form, [key]: !form[key] });

  const save = async () => {
    setError("");
    if (!form.name.trim()) { setError("Enter the person, business or grantor's name."); return; }
    setBusy(true);
    try {
      const response = await axios.post(`${API}/game/play/${token}/relationships`, form);
      setData((current) => ({ ...current, entries: [...current.entries, response.data.entry] }));
      setForm(EMPTY);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      window.scrollTo({ top: 0 });
    } catch {
      setError("We could not save this relationship. Please try again.");
    }
    setBusy(false);
  };

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 760, margin: "0 auto", padding: "30px 20px 80px" }} data-testid="bfg-relationship-mapping-page">
        <p className="bfg-eyebrow">{data.organization_name}</p>
        <h1 data-testid="bfg-rm-heading">Relationship Mapping</h1>
        <p style={{ marginTop: 14 }}>
          List all the people, businesses and grantors you know who match the ideal funder profiles identified in your organization's fundraising strategy.
        </p>
        <p style={{ marginTop: 10 }}>
          You are not being asked to know everyone.
        </p>
        <p style={{ marginTop: 10 }}>
          Simply think through your personal, professional, business and community relationships and add anyone who may genuinely match the funder profiles your board identified.
        </p>

        {data.entries.length > 0 && (
          <div className="bfg-card" style={{ marginTop: 22, padding: 18 }} data-testid="bfg-rm-saved-list">
            <h3>Relationships You Have Added ({data.entries.length})</h3>
            {data.entries.map((entry) => (
              <div className="bfg-summary-row" key={entry.relationship_id} data-testid={`bfg-rm-entry-${entry.relationship_id}`}>
                <span>{entry.name}{entry.organization ? ` — ${entry.organization}` : ""}</span>
                <strong>{entry.funder_type}</strong>
              </div>
            ))}
          </div>
        )}
        {saved && <p className="bfg-success" style={{ marginTop: 14 }} data-testid="bfg-rm-saved-note">Relationship saved. Add another below.</p>}

        <div className="bfg-card" style={{ marginTop: 22, padding: 18, textAlign: "left" }} data-testid="bfg-rm-form">
          <h3>Add A Relationship</h3>
          <label className="bfg-field" style={{ marginTop: 10 }}>
            <span>Funder Type <b>*</b></span>
            <select value={form.funder_type} onChange={set("funder_type")} data-testid="bfg-rm-funder-type">
              {["Individual", "Business", "Grantor"].map((type) => <option key={type} value={type}>{type}</option>)}
            </select>
          </label>
          <label className="bfg-field"><span>Name <b>*</b></span>
            <input value={form.name} onChange={set("name")} data-testid="bfg-rm-name" />
          </label>
          <label className="bfg-field"><span>Organization / Company{form.funder_type === "Individual" ? " (optional)" : ""}</span>
            <input value={form.organization} onChange={set("organization")} data-testid="bfg-rm-organization" />
          </label>
          <div className="bfg-two-col">
            <label className="bfg-field"><span>Email</span>
              <input value={form.email} onChange={set("email")} data-testid="bfg-rm-email" />
            </label>
            <label className="bfg-field"><span>Phone</span>
              <input value={form.phone} onChange={set("phone")} data-testid="bfg-rm-phone" />
            </label>
          </div>
          <label className="bfg-field"><span>Other Contact Details (optional)</span>
            <input value={form.other_contact} onChange={set("other_contact")} data-testid="bfg-rm-other-contact" />
          </label>
          <label className="bfg-field"><span>How Do You Know Them?</span>
            <textarea rows={3} value={form.how_know} onChange={set("how_know")} data-testid="bfg-rm-how-know" />
          </label>
          <label className="bfg-field"><span>Why Do You Think They Match The Ideal Funder Profile?</span>
            <textarea rows={3} value={form.why_match} onChange={set("why_match")} data-testid="bfg-rm-why-match" />
          </label>
          <p style={{ fontWeight: 700, marginTop: 14 }}>Are You Willing To:</p>
          {WILLING.map(([key, label]) => (
            <label key={key} className="bfg-ht-check" data-testid={`bfg-rm-${key}`}>
              <input type="checkbox" checked={form[key]} onChange={toggle(key)} /><span>{label}</span>
            </label>
          ))}
          {error && <p className="bfg-error" data-testid="bfg-rm-error">{error}</p>}
          <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 16 }} disabled={busy} onClick={save} data-testid="bfg-rm-add-btn">
            {busy ? "Saving…" : "Add Another Relationship"}
          </button>
        </div>
      </main>
    </BfgShell>
  );
}

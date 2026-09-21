import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import "./strategic-planning-dashboard.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategicLeadershipAssistantPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    axios.get(`${API}/guided/strategic-planning/leadership-assistant/${token}`)
      .then((response) => {
        setData(response.data);
        setMessages(response.data.messages || []);
      })
      .catch((err) => setError(err.response?.data?.detail || "This assistant is unavailable."));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const expired = data?.access_status === "renewal_required";

  const send = async (material = "") => {
    const message = text.trim() || material;
    if (!message || expired) return;
    setBusy(true);
    setText("");
    setError("");
    setMessages((current) => [...current, { role: "user", text: message }]);
    try {
      const response = await axios.post(`${API}/guided/strategic-planning/leadership-assistant/${token}`, {
        message,
        material_type: material,
      });
      setMessages((current) => [...current, { role: "assistant", text: response.data.answer }]);
    } catch (err) {
      setError(err.response?.data?.detail || "We could not complete that request.");
    }
    setBusy(false);
  };

  return (
    <main className="guided-page sp-dashboard">
      <section className="guided-section">
        <p className="bfg-eyebrow">{data?.organization_name || "STRATEGIC PLAN EXECUTION"}</p>
        <h1>{data ? `${data.member_name}'s Executive Assistant` : "Executive Assistant"}</h1>
        <p>Bookmark this secure page. It uses the approved Strategic Plan and the responsibility delegated to you during the Board's planning process.</p>

        {data && (
          <>
            <div className="sp-contentbox">
              <h3>Your Delegated Responsibility</h3>
              {(data.responsibilities || []).length > 0
                ? <ul>{data.responsibilities.map((item, index) => <li key={index}>{item}</li>)}</ul>
                : <p>{(data.areas || []).join(", ")}</p>}
              {data.included_until && !expired && (
                <p><strong>Included Executive Assistant access:</strong> through {new Date(data.included_until).toLocaleDateString()}.</p>
              )}
            </div>

            {expired ? (
              <div className="sp-contentbox">
                <h3>Executive Assistant Access Needs Renewal</h3>
                <p>{data.renewal_message || "Please ask your organization leader to renew Board Execution Support."}</p>
                {data.leader_name && <p><strong>Organization leader:</strong> {data.leader_name}</p>}
                <p>Your previous conversation remains available below.</p>
              </div>
            ) : (
              <div className="sp-contentbox">
                <h3>Create A Resource</h3>
                <div className="sp-actions">
                  {(data.suggested_materials || []).map((item) => (
                    <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => send(item)} disabled={busy} key={item}>{item}</button>
                  ))}
                </div>
              </div>
            )}

            <div className="sp-contentbox">
              <h3>Ask For Help</h3>
              {messages.map((message, index) => (
                <article className="choice" key={index}>
                  <strong>{message.role === "assistant" ? "Your Assistant" : "You"}</strong>
                  <span style={{ whiteSpace: "pre-wrap" }}>{message.text}</span>
                </article>
              ))}
              {!expired && (
                <>
                  <textarea rows={6} value={text} onChange={(event) => setText(event.target.value)} placeholder="Ask what to do next, or request a message, plan, checklist, resource or Board update." />
                  <button className="bfg-btn bfg-btn-primary" onClick={() => send()} disabled={busy || !text.trim()}>{busy ? "CREATING…" : "SEND"}</button>
                </>
              )}
            </div>
          </>
        )}

        {error && <p className="bfg-error">{error}</p>}
      </section>
    </main>
  );
}

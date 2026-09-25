import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import "./game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function BoardExecutionAssistantPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    axios.get(`${API}/board-assistant/${token}`)
      .then((response) => {
        setData(response.data);
        setMessages(response.data.messages || []);
      })
      .catch((err) => setError(err.response?.data?.detail || "This assistant link is not available."));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const expired = data?.access_status === "renewal_required";

  const send = async (material = "") => {
    const message = text.trim() || `Create my ${material}`;
    if (!message || expired) return;
    setBusy(true);
    setError("");
    setMessages((current) => [...current, { role: "user", text: message }]);
    setText("");
    try {
      const response = await axios.post(`${API}/board-assistant/${token}`, { message, material_type: material });
      setMessages((current) => [...current, { role: "assistant", text: response.data.answer }]);
    } catch (err) {
      setError(err.response?.data?.detail || "We could not complete that request.");
    }
    setBusy(false);
  };

  return (
    <div className="bfg-pf-page">
      <main className="bfg-pf-doc">
        <p className="bfg-pf-eyebrow">{data?.organization_name || "BOARD FUNDRAISING EXECUTION"}</p>
        <h1>{data ? `${data.member_name}'s Executive Assistant` : "Your Executive Assistant"}</h1>
        <p className="bfg-pf-sub">Bookmark this secure page. It uses your organization's adopted fundraising strategy, your approved portfolio and your own relationship information to help you execute the role you accepted.</p>

        {data?.included_until && !expired && (
          <section className="bfg-pf-section">
            <p><strong>Included Executive Assistant access:</strong> through {new Date(data.included_until).toLocaleDateString()}.</p>
          </section>
        )}

        {expired ? (
          <section className="bfg-pf-section">
            <h2>Executive Assistant Access Needs Renewal</h2>
            <p>{data.renewal_message || "Please ask your organization leader to renew Board Execution Support."}</p>
            {data.leader_name && <p><strong>Organization leader:</strong> {data.leader_name}</p>}
            <p>Your previous conversation remains available below.</p>
          </section>
        ) : data?.suggested_materials?.length > 0 && (
          <section className="bfg-pf-section">
            <h2>Recommended For Your Role</h2>
            <p className="bfg-pf-sub">Choose a material only when you are ready to use it. Your assistant will create it from the adopted strategy and the responsibilities in your approved Portfolio.</p>
            <div className="bfg-pf-actions">
              {data.suggested_materials.map((item) => <button className="bfg-pf-btn ghost" disabled={busy} onClick={() => send(item)} key={item}>{item}</button>)}
            </div>
          </section>
        )}

        <section className="bfg-pf-section">
          <h2>Ask For Help</h2>
          {messages.map((message, index) => (
            <div className="bfg-pf-item" key={index}>
              <strong>{message.role === "assistant" ? "Your Assistant" : "You"}</strong>
              <p style={{ whiteSpace: "pre-wrap" }}>{message.text}</p>
            </div>
          ))}
          {!expired && (
            <>
              <textarea className="bfg-pf-textarea" rows={5} value={text} onChange={(event) => setText(event.target.value)} placeholder="Ask what to do next, request a message, script, checklist or other fundraising help." />
              <button className="bfg-pf-btn" disabled={busy || !text.trim()} onClick={() => send()}>{busy ? "CREATING…" : "SEND"}</button>
            </>
          )}
          {error && <p className="bfg-error">{error}</p>}
        </section>
      </main>
    </div>
  );
}

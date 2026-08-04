import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import { Check, Copy, MessageSquareText } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function TrackedActionPage({ type }) {
  const [params] = useSearchParams();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    const token = params.get("token");
    if (!token) { setError("This secure action link is invalid or expired."); return; }
    axios.post(`${API}/tracked-actions/${type}`, { token }).then((response) => {
      setResult(response.data);
      if (/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)) {
        window.location.href = `sms:${response.data.phone}?body=${encodeURIComponent(response.data.message)}`;
      }
    }).catch((requestError) => setError(requestError.response?.data?.detail || "This secure action link is invalid or expired."));
  }, [params, type]);
  const copyMessage = async () => { await navigator.clipboard.writeText(result.message); setCopied(true); };
  return <main className="tracked-action-page" data-testid={`${type}-page`}><section className="tracked-action-card"><div className="confirmation-icon"><MessageSquareText size={34} /></div><p className="eyebrow">Nonprofit Board Builder</p><h1>{type === "board-transformation-ready" ? "Text I Am Ready" : "Confirm I Am Available"}</h1>{!result && !error && <p data-testid="tracked-action-loading">Preparing your secure message…</p>}{error && <p className="submit-error" data-testid="tracked-action-error">{error}</p>}{result && <div data-testid="tracked-action-details"><p>Your tracked action has been recorded as <strong>{result.status}</strong>. A click confirms that you opened this text-message action; it does not confirm that a text was sent.</p><div className="text-message-preview"><span>Send to</span><strong data-testid="tracked-action-phone">{result.display_phone}</strong><span>Prepared message</span><p data-testid="tracked-action-message">{result.message}</p></div><button className="button" onClick={copyMessage} data-testid="copy-tracked-message-button">{copied ? <Check size={17} /> : <Copy size={17} />}{copied ? "Message Copied" : "Copy Message"}</button></div>}</section></main>;
}
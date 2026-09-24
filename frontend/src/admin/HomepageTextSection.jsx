import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { RefreshCw, Save } from "lucide-react";
import { HOMEPAGE_KEYS } from "@/clean/platform";
import { MAIN_HOME_DEFAULTS } from "@/pages/MainHomePage";
import { FACILITATED_GAME_HOME_DEFAULTS } from "@/game/FacilitatedGamePage";
import { recruitmentHomeContent } from "@/content/siteContent";
import { GUIDED_PRODUCT_CONFIG } from "@/funnels/GuidedProductPages";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });

const stripIcon = (value) => {
  const { icon, ...copy } = value || {};
  return copy;
};

const LOCAL_DEFAULTS = {
  main: MAIN_HOME_DEFAULTS,
  recruitment: recruitmentHomeContent,
  "strategic-planning": stripIcon(GUIDED_PRODUCT_CONFIG["strategic-planning"]),
  "board-recommitment": stripIcon(GUIDED_PRODUCT_CONFIG["board-recommitment"]),
  "facilitated-game": FACILITATED_GAME_HOME_DEFAULTS,
};

const prettyLabel = (value) => String(value)
  .replace(/_/g, " ")
  .replace(/([a-z])([A-Z])/g, "$1 $2")
  .replace(/\b\w/g, (letter) => letter.toUpperCase());

const cloneContent = (value) => JSON.parse(JSON.stringify(value ?? {}));

const setContentAtPath = (content, path, value) => {
  const next = cloneContent(content);
  let cursor = next;
  path.slice(0, -1).forEach((segment) => { cursor = cursor[segment]; });
  cursor[path[path.length - 1]] = value;
  return next;
};

const lockedTextKey = (key) => /(?:_url|_href|_route|_path|_link)$/i.test(String(key));

const flattenContent = (value, path = [], label = "") => {
  const rows = [];
  if (Array.isArray(value)) {
    value.forEach((item, index) => {
      rows.push(...flattenContent(item, [...path, index], `${label || "Item"} ${index + 1}`));
    });
    return rows;
  }
  if (value && typeof value === "object") {
    Object.entries(value)
      .filter(([key]) => !lockedTextKey(key))
      .forEach(([key, item]) => {
        rows.push(...flattenContent(item, [...path, key], prettyLabel(key)));
      });
    return rows;
  }
  rows.push({ path, label, value });
  return rows;
};

function HomepageField({ row, onChange }) {
  const { path, label, value } = row;

  if (typeof value === "boolean") {
    return (
      <label className="terms-check" style={{ margin: "12px 0" }}>
        <input type="checkbox" checked={value} onChange={(event) => onChange(path, event.target.checked)} />
        <span>{label}</span>
      </label>
    );
  }

  if (typeof value === "number") {
    return (
      <label className="admin-notes">
        <strong>{label}</strong>
        <input type="number" value={value} onChange={(event) => onChange(path, Number(event.target.value))} />
      </label>
    );
  }

  const text = value == null ? "" : String(value);
  const long = text.length > 90 || /text|headline|heading|sub|promise|description|title|outcome|step|intro|note/i.test(label);

  return (
    <label className="admin-notes" style={{ margin: "12px 0" }}>
      <strong>{label}</strong>
      {long ? (
        <textarea
          rows={Math.min(8, Math.max(2, Math.ceil(Math.max(text.length, 80) / 90)))}
          value={text}
          onChange={(event) => onChange(path, event.target.value)}
        />
      ) : (
        <input value={text} onChange={(event) => onChange(path, event.target.value)} />
      )}
    </label>
  );
}

export function HomepageTextSection() {
  const [pageKey, setPageKey] = useState(HOMEPAGE_KEYS[0][0]);
  const [content, setContent] = useState({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(async (key) => {
    setMessage("");
    try {
      const stored = (await axios.get(`${API}/platform/homepages/${key}`)).data.content || {};
      let defaults = LOCAL_DEFAULTS[key] || {};
      if (key === "board-fundraising-game") {
        defaults = (await axios.get(`${API}/game/content`)).data.content || {};
      }
      setContent({ ...cloneContent(defaults), ...cloneContent(stored) });
    } catch (error) {
      setMessage(error.response?.data?.detail || "Could not load this home page text.");
    }
  }, []);

  useEffect(() => { load(pageKey); }, [pageKey, load]);

  const updateField = (path, value) => setContent((current) => setContentAtPath(current, path, value));

  const save = async () => {
    setSaving(true);
    setMessage("");
    try {
      await client.put(`/admin/platform/homepages/${pageKey}`, { content });
      setMessage("Home page text saved.");
    } catch (error) {
      setMessage(error.response?.data?.detail || "Could not save this home page.");
    }
    setSaving(false);
  };

  const fields = flattenContent(content);

  return (
    <section data-testid="clean-homepage-editor">
      <div className="admin-funnel-numbers-head">
        <div>
          <h2>Home Page Text Edit</h2>
          <p>Choose one of the six public home pages and edit its words directly. Routes, dashboard destinations and product connections stay locked outside this editor.</p>
        </div>
      </div>
      <div className="admin-filters">
        <label>
          Home Page
          <select value={pageKey} onChange={(event) => setPageKey(event.target.value)}>
            {HOMEPAGE_KEYS.map(([key, name]) => <option key={key} value={key}>{name}</option>)}
          </select>
        </label>
        <button className="button button-back button-small" onClick={() => load(pageKey)}><RefreshCw size={15} /> Reload Saved Text</button>
      </div>
      <div className="admin-homepage-text-fields">
        {fields.map((row, index) => (
          <HomepageField key={row.path.join(".") || index} row={row} onChange={updateField} />
        ))}
      </div>
      {message && <p className="admin-message">{message}</p>}
      <button className="button" disabled={saving} onClick={save}>
        <Save size={15} /> {saving ? "SAVING…" : "SAVE HOME PAGE TEXT"}
      </button>
    </section>
  );
}

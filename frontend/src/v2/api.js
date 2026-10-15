import axios from "axios";

export const API_BASE = `${(process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "")}/api/v2`;
export const adminTestApiPath = (path) => /^\/(journeys|forms|meeting)\/admin-test-[^/?]+/.test(path || "") ? `/admin/test-api${path}` : path;
export const resourceUrl = (path) => `${API_BASE}${adminTestApiPath(path.startsWith("/") ? path : `/${path}`)}`;
export const errorMessage = (error, fallback = "We could not complete that action. Please try again.") => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (error?.response?.status === 401 || error?.response?.status === 403) return "Please use your secure email link to open this resource, or recover your access.";
  return fallback;
};

export const draftKey = (journeyId) => `nbb:v2:draft:${journeyId}`;
const sessionFallback = new Map();
export const readSessionValue = (key) => {
  try { return sessionStorage.getItem(key) || sessionFallback.get(key) || ""; }
  catch { return sessionFallback.get(key) || ""; }
};
const saveSessionValue = (key, value) => {
  sessionFallback.set(key, value);
  try { sessionStorage.setItem(key, value); } catch { /* Access remains available in this open tab. */ }
};
export const saveDraftAccess = (journeyId, token, product) => {
  saveSessionValue(draftKey(journeyId), token);
  if (product) saveSessionValue(`nbb:v2:current:${product}`, journeyId);
};
export const v2Api = axios.create({ baseURL: API_BASE, withCredentials: true });
v2Api.interceptors.request.use((config) => {
  const originalPath = config.url;
  let memberToken = "";
  try { memberToken = localStorage.getItem("memberToken") || ""; } catch { /* Scoped owner cookies still authorize resource access. */ }
  if (memberToken) config.headers.Authorization = `Bearer ${memberToken}`;
  const match = config.url?.match(/^\/journeys\/([^/?]+)/);
  const draft = match && readSessionValue(draftKey(decodeURIComponent(match[1])));
  if (draft) config.headers["X-V2-Draft"] = draft;
  config.url = adminTestApiPath(originalPath);
  return config;
});

import axios from "axios";
import { previewHeaders } from "../adminPreview";

export const memberApi = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
});

memberApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("memberToken");
  const operateAs = sessionStorage.getItem("operateAsUserId");
  const preview = previewHeaders();
  if (Object.keys(preview).length > 0) {
    Object.assign(config.headers, preview);
    delete config.headers.Authorization;
  } else if (operateAs) {
    config.headers["X-Operate-As"] = operateAs;
    delete config.headers.Authorization;
  } else if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const storeMemberToken = (token) => { if (token) localStorage.setItem("memberToken", token); };
export const clearMemberToken = () => localStorage.removeItem("memberToken");

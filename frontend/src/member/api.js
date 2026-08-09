import axios from "axios";

export const memberApi = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
});

memberApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("memberToken");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const storeMemberToken = (token) => { if (token) localStorage.setItem("memberToken", token); };
export const clearMemberToken = () => localStorage.removeItem("memberToken");

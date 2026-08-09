import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { clearMemberToken, memberApi, storeMemberToken } from "./api";

const MemberAuthContext = createContext(null);

export const MemberAuthProvider = ({ children }) => {
  const [member, setMember] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const response = await memberApi.get("/members/me");
      setMember(response.data.member);
      return response.data.member;
    } catch {
      setMember(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const login = useCallback(async (email, password, sessionId) => {
    const response = await memberApi.post("/members/login", { email, password, session_id: sessionId || "" });
    storeMemberToken(response.data.token);
    setMember(response.data.member);
    return response.data;
  }, []);

  const register = useCallback(async (payload) => {
    const response = await memberApi.post("/members/register", payload);
    storeMemberToken(response.data.token);
    setMember(response.data.member);
    return response.data;
  }, []);

  const logout = useCallback(async () => {
    try { await memberApi.post("/members/logout"); } catch { /* ignore */ }
    clearMemberToken();
    setMember(null);
  }, []);

  const value = useMemo(() => ({ member, loading, login, register, logout, refresh, setMember }), [member, loading, login, register, logout, refresh]);
  return <MemberAuthContext.Provider value={value}>{children}</MemberAuthContext.Provider>;
};

export const useMemberAuth = () => useContext(MemberAuthContext);

import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { api, tokens } from "./api";
import type { Role, User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (role: "parent" | "tutor", data: Record<string, string>) => Promise<User>;
  logout: () => void;
  refresh: () => Promise<User | null>;
}

const Ctx = createContext<AuthState | null>(null);

export const homeFor = (role: Role) => (role === "admin" ? "/admin" : role === "tutor" ? "/tutor" : "/parent");

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(tokens.access || tokens.refresh));

  const refresh = useCallback(async () => {
    try {
      const u = await api.get<User>("/auth/me/");
      setUser(u);
      return u;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    if (tokens.access || tokens.refresh) refresh().finally(() => setLoading(false));
    else setLoading(false);
  }, [refresh]);

  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener("tc:logout", onLogout);
    return () => window.removeEventListener("tc:logout", onLogout);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const r = await api.post<{ access: string; refresh: string; user: User }>("/auth/token/", { email, password });
    tokens.save(r.access, r.refresh);
    setUser(r.user);
    return r.user;
  }, []);

  const register = useCallback(
    async (role: "parent" | "tutor", data: Record<string, string>) => {
      await api.post(`/auth/register/${role}/`, data);
      return login(data.email, data.password);
    },
    [login],
  );

  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
  }, []);

  return <Ctx.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}

import { createContext, use } from "react";

import type { Role } from "@/api/types";

export type Session = { role: Role; displayName: string };

export type AuthContextValue = {
  session: Session | null;
  login: (username: string, password: string) => Promise<Session>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = use(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

export const HOME_BY_ROLE: Record<Role, string> = {
  patient: "/book",
  clinician: "/schedule",
  admin: "/admin",
};

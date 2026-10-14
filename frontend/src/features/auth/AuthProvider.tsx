import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useState, type ReactNode } from "react";

import { api, setAccessToken } from "@/api/client";
import type { TokenResponse } from "@/api/types";

import { AuthContext, type Session } from "./session";

/**
 * Holds the signed-in session. The access token lives only in memory (see api/client.ts):
 * reloading the page signs the user out, which is the right trade-off for health data on
 * shared computers. A real IdP would add silent re-authentication.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const queryClient = useQueryClient();

  const login = useCallback(async (username: string, password: string) => {
    const token = await api<TokenResponse>("/auth/token", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    setAccessToken(token.access_token);
    const next = { role: token.role, displayName: token.display_name };
    setSession(next);
    return next;
  }, []);

  const logout = useCallback(() => {
    setAccessToken(null);
    setSession(null);
    queryClient.clear(); // drop cached patient data from memory on sign-out
  }, [queryClient]);

  const value = useMemo(() => ({ session, login, logout }), [session, login, logout]);
  return <AuthContext value={value}>{children}</AuthContext>;
}

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { api, setAccessToken, setTokenRefresher } from "@/api/client";
import type { TokenResponse } from "@/api/types";

import { AuthContext, type Session } from "./session";

/**
 * Holds the signed-in session. The access token lives only in memory (see api/client.ts); the
 * session survives a reload through an HttpOnly refresh cookie that script cannot read. It
 * is a browser-session cookie, so closing the browser still signs out on shared computers
 * (ADR-0012).
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [restoring, setRestoring] = useState(true);
  const queryClient = useQueryClient();
  const inFlightRefresh = useRef<Promise<boolean> | null>(null);
  const pendingLogout = useRef<Promise<unknown>>(Promise.resolve());

  const start = useCallback((token: TokenResponse): Session => {
    setAccessToken(token.access_token);
    const next = { role: token.role, displayName: token.display_name };
    setSession(next);
    return next;
  }, []);

  const clear = useCallback(() => {
    setAccessToken(null);
    setSession(null);
    queryClient.clear(); // drop cached patient data from memory on sign-out
  }, [queryClient]);

  // One refresh shared by every caller: page load (twice in StrictMode) and any number of
  // queries whose access token expired at the same moment.
  const refresh = useCallback((): Promise<boolean> => {
    inFlightRefresh.current ??= api<TokenResponse>("/auth/refresh", { method: "POST" })
      .then((token) => {
        start(token);
        return true;
      })
      .catch(() => {
        clear();
        return false;
      })
      .finally(() => {
        inFlightRefresh.current = null;
      });
    return inFlightRefresh.current;
  }, [start, clear]);

  useEffect(() => {
    setTokenRefresher(refresh);
    void refresh().finally(() => {
      setRestoring(false);
    });
    return () => {
      setTokenRefresher(null);
    };
  }, [refresh]);

  const login = useCallback(
    async (username: string, password: string) => {
      // A slow logout response must not clear the cookie of the session started after it.
      await pendingLogout.current;
      return start(
        await api<TokenResponse>("/auth/token", {
          method: "POST",
          body: JSON.stringify({ username, password }),
        }),
      );
    },
    [start],
  );

  const logout = useCallback(() => {
    // Clear the HttpOnly cookie server-side, or the next reload would sign the user back in.
    pendingLogout.current = api("/auth/logout", { method: "POST" }).catch(() => undefined);
    clear();
  }, [clear]);

  const value = useMemo(() => ({ session, login, logout }), [session, login, logout]);

  // Route guards would bounce a returning user to /login before the session is restored.
  if (restoring) {
    return (
      <p role="status" className="p-6 text-sm text-ink-muted">
        Loading...
      </p>
    );
  }
  return <AuthContext value={value}>{children}</AuthContext>;
}

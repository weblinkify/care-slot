/**
 * Session restore and silent renewal. The refresh cookie itself is HttpOnly and invisible to
 * script, so these tests drive the endpoints that use it and check what the app does next.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";

import { AuthProvider } from "./AuthProvider";
import { useAuth } from "./session";

type Route = (init: RequestInit) => Response;

function json(status: number, body: unknown): Response {
  const type = status < 400 ? "application/json" : "application/problem+json";
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": type } });
}

const token = (access: string) =>
  json(200, {
    access_token: access,
    token_type: "bearer",
    expires_in: 900,
    role: "patient",
    display_name: "Aino (patient)",
  });

const unauthenticated = () =>
  json(401, { type: "about:blank", title: "Unauthorized", status: 401 });

/** Fake API: each path answers from its queue of responses, in order. */
function fakeApi(routes: Record<string, Route[]>) {
  const fetchMock = vi.fn((url: string, init: RequestInit) => {
    const path = new URL(url, "http://app.test").pathname.replace("/api/v1", "");
    const next = routes[path]?.shift();
    if (!next) throw new Error(`unexpected request ${path}`);
    return Promise.resolve(next(init));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function WhoAmI() {
  const { session } = useAuth();
  return <p>{session ? `signed in as ${session.displayName}` : "signed out"}</p>;
}

function renderApp() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthProvider>
        <WhoAmI />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AuthProvider", () => {
  it("restores the session after a reload from the refresh cookie", async () => {
    const fetchMock = fakeApi({ "/auth/refresh": [() => token("t1")] });
    renderApp();

    expect(await screen.findByText("signed in as Aino (patient)")).toBeInTheDocument();
    // The browser only attaches the cookie when credentials are included.
    expect(fetchMock.mock.calls[0]?.[1].credentials).toBe("include");
  });

  it("shows the signed-out app when there is no session to restore", async () => {
    fakeApi({ "/auth/refresh": [unauthenticated] });
    renderApp();

    expect(await screen.findByText("signed out")).toBeInTheDocument();
  });

  it("renews an expired access token once and retries the request", async () => {
    const seen: (string | null)[] = [];
    const clinics: Route = (init) => {
      const auth = new Headers(init.headers).get("Authorization");
      seen.push(auth);
      return auth === "Bearer fresh" ? json(200, ["clinic"]) : unauthenticated();
    };
    fakeApi({
      "/auth/refresh": [() => token("expired"), () => token("fresh")],
      "/clinics": [clinics, clinics],
    });
    renderApp();
    await screen.findByText("signed in as Aino (patient)");

    await expect(api("/clinics")).resolves.toEqual(["clinic"]);
    expect(seen).toEqual(["Bearer expired", "Bearer fresh"]);
  });

  it("signs out when the session cannot be renewed", async () => {
    fakeApi({
      "/auth/refresh": [() => token("expired"), unauthenticated],
      "/clinics": [unauthenticated],
    });
    renderApp();
    await screen.findByText("signed in as Aino (patient)");

    await expect(api("/clinics")).rejects.toMatchObject({ status: 401 });
    expect(await screen.findByText("signed out")).toBeInTheDocument();
  });
});

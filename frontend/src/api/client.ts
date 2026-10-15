/**
 * Thin fetch wrapper for the CareSlot API.
 *
 * Every non-2xx response from the backend is an RFC 7807 problem document, so the UI has one
 * error type (`ApiError`) and one way to show errors.
 */

export type Problem = {
  type: string;
  title: string;
  status: number;
  detail?: string;
  errors?: { loc: (string | number)[]; msg: string }[];
};

export class ApiError extends Error {
  constructor(readonly problem: Problem) {
    super(problem.detail ?? problem.title);
    this.name = "ApiError";
  }

  get status(): number {
    return this.problem.status;
  }
}

const BASE_URL = import.meta.env.VITE_API_URL ?? "";

const AUTH_PATH = "/auth/";

let accessToken: string | null = null;
let refreshAccessToken: (() => Promise<boolean>) | null = null;

export function setAccessToken(token: string | null): void {
  // Kept in memory only (not localStorage): a token in storage is readable by any XSS payload.
  // Reloads are survived by the HttpOnly refresh cookie instead (ADR-0012).
  accessToken = token;
}

/** Registered by the AuthProvider: renews the access token from the refresh cookie. */
export function setTokenRefresher(refresher: (() => Promise<boolean>) | null): void {
  refreshAccessToken = refresher;
}

function send(path: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  // Only the auth endpoints need the refresh cookie. The browser attaches it (this code never
  // sees it); "include" because locally the API is on another origin.
  const credentials = path.startsWith(AUTH_PATH) ? "include" : "same-origin";
  return fetch(`${BASE_URL}/api/v1${path}`, { ...init, headers, credentials });
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response = await send(path, init);

  // Access tokens live 15 minutes. On expiry, renew once from the refresh cookie and retry.
  if (
    response.status === 401 &&
    accessToken &&
    refreshAccessToken &&
    !path.startsWith(AUTH_PATH) &&
    (await refreshAccessToken())
  ) {
    response = await send(path, init);
  }

  if (!response.ok) {
    const isProblem = response.headers.get("content-type")?.includes("json") ?? false;
    const problem: Problem = isProblem
      ? ((await response.json()) as Problem)
      : { type: "about:blank", title: response.statusText, status: response.status };
    throw new ApiError(problem);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

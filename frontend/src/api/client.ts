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

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  // Kept in memory only (not localStorage): a token in storage is readable by any XSS payload.
  accessToken = token;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`${BASE_URL}/api/v1${path}`, { ...init, headers });

  if (!response.ok) {
    const isProblem = response.headers.get("content-type")?.includes("json") ?? false;
    const problem: Problem = isProblem
      ? ((await response.json()) as Problem)
      : { type: "about:blank", title: response.statusText, status: response.status };
    throw new ApiError(problem);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

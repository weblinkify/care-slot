/**
 * The demo API must behave like the real one for everything a client can see in a demo.
 * These tests pin the rules that matter: ownership, double booking, the change cut-off,
 * purpose-bound record access and the audit trail.
 */
import { setupServer } from "msw/node";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { Appointment, AuditEntry, ChainVerification, Slot } from "@/api/types";

import { CLINICIANS, createDemoState, DEMO_USERS, type DemoState } from "./db";
import { createHandlers, memorySessionStore } from "./handlers";

const BASE = "http://demo.test/api/v1";
let state: DemoState;
let now = new Date("2026-03-02T08:00:00Z"); // a Monday
const server = setupServer();

beforeAll(() => {
  server.listen({ onUnhandledFrame: "error" });
});
afterAll(() => {
  server.close();
});
beforeEach(() => {
  now = new Date("2026-03-02T08:00:00Z");
  state = createDemoState(now);
  server.resetHandlers(...createHandlers(state, () => now, undefined, memorySessionStore()));
});

async function token(username: string): Promise<string> {
  const res = await fetch(`${BASE}/auth/token`, {
    method: "POST",
    body: JSON.stringify({ username, password: "demo-password" }),
  });
  return ((await res.json()) as { access_token: string }).access_token;
}

function call(path: string, auth: string, init: RequestInit = {}) {
  return fetch(`${BASE}${path}`, { ...init, headers: { Authorization: `Bearer ${auth}` } });
}

async function firstFreeSlot(auth: string): Promise<Slot> {
  const params = new URLSearchParams({
    from: "2026-03-04T00:00:00Z",
    to: "2026-03-05T00:00:00Z",
  });
  const res = await call(`/clinicians/${CLINICIANS[1].id}/slots?${params.toString()}`, auth);
  const slots = (await res.json()) as Slot[];
  const slot = slots[0];
  if (!slot) throw new Error("no free slot in fixture");
  return slot;
}

async function book(auth: string, slotId: string) {
  return call("/appointments", auth, { method: "POST", body: JSON.stringify({ slot_id: slotId }) });
}

describe("demo API", () => {
  it("rejects wrong passwords with problem+json", async () => {
    const res = await fetch(`${BASE}/auth/token`, {
      method: "POST",
      body: JSON.stringify({ username: "aino", password: "nope" }),
    });
    expect(res.status).toBe(401);
    expect(res.headers.get("content-type")).toContain("application/problem+json");
  });

  it("restores a session after a reload until sign-out, like the refresh cookie", async () => {
    const refresh = () => fetch(`${BASE}/auth/refresh`, { method: "POST" });
    expect((await refresh()).status).toBe(401);

    await token("dr.aava");
    const restored = await refresh();
    expect(restored.status).toBe(200);
    expect(await restored.json()).toMatchObject({
      access_token: `demo:${DEMO_USERS["dr.aava"]?.subject ?? ""}`,
      role: "clinician",
    });

    expect((await fetch(`${BASE}/auth/logout`, { method: "POST" })).status).toBe(204);
    expect((await refresh()).status).toBe(401);
  });

  it("prevents double booking", async () => {
    const aino = await token("aino");
    const eero = await token("eero");
    const slot = await firstFreeSlot(aino);

    expect((await book(aino, slot.id)).status).toBe(201);
    const second = await book(eero, slot.id);
    expect(second.status).toBe(409);
  });

  it("hides other patients' appointments (404, not 403)", async () => {
    const aino = await token("aino");
    const eero = await token("eero");
    const appt = (await (await book(aino, (await firstFreeSlot(aino)).id)).json()) as Appointment;

    const res = await call(`/appointments/${appt.id}/cancel`, eero, { method: "POST" });
    expect(res.status).toBe(404);
  });

  it("does not leak patient ids in responses", async () => {
    const aino = await token("aino");
    const appt = (await (await book(aino, (await firstFreeSlot(aino)).id)).json()) as object;
    expect(appt).not.toHaveProperty("patient_id");
  });

  it("enforces the 2-hour change cut-off", async () => {
    const aino = await token("aino");
    const slot = await firstFreeSlot(aino);
    const appt = (await (await book(aino, slot.id)).json()) as Appointment;

    now = new Date(new Date(slot.starts_at).getTime() - 60 * 60 * 1000); // 1h before
    const res = await call(`/appointments/${appt.id}/cancel`, aino, { method: "POST" });
    expect(res.status).toBe(422);
  });

  it("only lets clinicians read the day schedule", async () => {
    const aino = await token("aino");
    const res = await call("/clinicians/me/schedule?day=2026-03-03", aino);
    expect(res.status).toBe(403);
  });

  it("lets a clinician open a record only with a care relationship and a clinical reason", async () => {
    const doctor = await token("dr.aava");
    const eero = DEMO_USERS.eero?.subject ?? "";
    // Book Eero with Dr. Aava to establish a care relationship.
    const eeroToken = await token("eero");
    const params = new URLSearchParams({
      from: "2026-03-04T00:00:00Z",
      to: "2026-03-05T00:00:00Z",
    });
    const slots = (await (
      await call(`/clinicians/${CLINICIANS[0].id}/slots?${params.toString()}`, eeroToken)
    ).json()) as Slot[];
    await book(eeroToken, slots[0]?.id ?? "");

    expect((await call(`/patients/${eero}`, doctor)).status).toBe(422); // no reason
    const ok = await call(`/patients/${eero}?reason=treatment`, doctor);
    expect(ok.status).toBe(200);
    expect(await ok.json()).toMatchObject({ identity_code_masked: "020794-****" });

    const stranger = await call(`/patients/${crypto.randomUUID()}?reason=treatment`, doctor);
    expect(stranger.status).toBe(404);
  });

  it("audits access and verifies the hash chain", async () => {
    const aino = await token("aino");
    await book(aino, (await firstFreeSlot(aino)).id);
    await call("/patients/me", aino);

    const admin = await token("admin");
    const log = (await (await call("/audit-log", admin)).json()) as AuditEntry[];
    expect(log.map((e) => e.action)).toEqual(["audit.search", "patient.read", "appointment.book"]);

    const verification = (await (
      await call("/audit-log/verify", admin)
    ).json()) as ChainVerification;
    expect(verification).toEqual({ valid: true, entries_checked: 3, first_invalid_id: null });
  });

  it("records consent decisions as history and erases a patient with the backend's fan-out", async () => {
    const aino = await token("aino");
    const put = (purpose: string, granted: boolean) =>
      call(`/consents/${purpose}`, aino, { method: "PUT", body: JSON.stringify({ granted }) });
    await put("research", true);
    await put("research", true); // idempotent
    await put("research", false);
    const overview = (await (await call("/consents", aino)).json()) as {
      history: { granted: boolean }[];
    };
    expect(overview.history.map((h) => h.granted)).toEqual([false, true]);

    const appt = (await (await book(aino, (await firstFreeSlot(aino)).id)).json()) as Appointment;
    const erase = (body: object) =>
      call("/patients/me/erasure", aino, { method: "POST", body: JSON.stringify(body) });
    expect((await erase({})).status).toBe(422);
    expect((await erase({ confirm: true })).status).toBe(200);
    expect((await erase({ confirm: true })).status).toBe(409);

    expect(state.appointments.find((a) => a.id === appt.id)?.status).toBe("cancelled");
    expect(state.consents).toEqual([]);
    expect(await (await call("/patients/me", aino)).json()).toMatchObject({
      full_name: "Erased patient",
      identity_code: null,
    });
  });
});

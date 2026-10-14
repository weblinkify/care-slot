/**
 * DEMO MODE ONLY - Mock Service Worker handlers implementing /api/v1 from the OpenAPI
 * contract. Errors are RFC 7807 problem documents, exactly like the real API.
 */
import { http, HttpResponse } from "msw";

import type { Appointment, TokenResponse } from "@/api/types";

import {
  CHANGE_CUTOFF_MS,
  clinics,
  createDemoState,
  dateInClinic,
  DEMO_USERS,
  isBooked,
  type DemoAppointment,
  type DemoState,
  type DemoUser,
} from "./db";

const API = "*/api/v1";
const DEMO_PASSWORD = "demo-password";

function problem(status: number, code: string, title: string, detail?: string) {
  return HttpResponse.json(
    {
      type: `https://careslot.example/problems/${code}`,
      title,
      status,
      ...(detail ? { detail } : {}),
    },
    { status, headers: { "Content-Type": "application/problem+json" } },
  );
}

const notFound = () => problem(404, "not-found", "Appointment not found");
const unauthenticated = () => problem(401, "unauthenticated", "Authentication required");
const forbidden = () => problem(403, "forbidden", "Not allowed");

/** Demo tokens are opaque handles to a demo user - nothing is signed in the browser. */
function principal(request: Request): DemoUser | null {
  const token = request.headers.get("Authorization")?.replace(/^Bearer demo:/, "");
  return Object.values(DEMO_USERS).find((u) => u.subject === token) ?? null;
}

/** The real API never returns patient_id in appointment responses; neither does the mock. */
function publicView(appointment: DemoAppointment): Appointment {
  const { patient_id, ...rest } = appointment;
  return rest;
}

export function createHandlers(
  state: DemoState = createDemoState(),
  now: () => Date = () => new Date(),
) {
  const changeWindowOpen = (a: DemoAppointment) =>
    now().getTime() <= new Date(a.starts_at).getTime() - CHANGE_CUTOFF_MS;

  function ownAppointment(user: DemoUser, id: string | readonly string[] | undefined) {
    const appt = state.appointments.find((a) => a.id === id);
    return appt && user.role === "patient" && appt.patient_id === user.subject ? appt : null;
  }

  function freeSlot(slotId: string) {
    const slot = state.slots.find((s) => s.id === slotId);
    if (!slot) return { error: problem(404, "not-found", "Slot not found") };
    if (isBooked(state, slotId))
      return { error: problem(409, "slot-unavailable", "Slot is no longer available") };
    if (new Date(slot.starts_at) <= now())
      return { error: problem(422, "slot-in-past", "Slot has already started") };
    return { slot };
  }

  function changeBlocked(appt: DemoAppointment) {
    if (appt.status !== "booked")
      return problem(409, "appointment-not-active", "Appointment is not active");
    if (!changeWindowOpen(appt))
      return problem(
        422,
        "change-window-closed",
        "Appointment can no longer be changed",
        "Changes are not possible later than 2:00:00 before the start time.",
      );
    return null;
  }

  return [
    http.post(`${API}/auth/token`, async ({ request }) => {
      const body = (await request.json()) as { username?: string; password?: string };
      const user = DEMO_USERS[(body.username ?? "").toLowerCase()];
      if (!user || body.password !== DEMO_PASSWORD)
        return problem(
          401,
          "unauthenticated",
          "Authentication required",
          "Invalid username or password",
        );
      return HttpResponse.json<TokenResponse>({
        access_token: `demo:${user.subject}`,
        token_type: "bearer",
        expires_in: 900,
        role: user.role,
        display_name: user.display_name,
      });
    }),

    http.get(`${API}/clinics`, ({ request }) =>
      principal(request) ? HttpResponse.json(clinics) : unauthenticated(),
    ),

    http.get(`${API}/clinicians/:id/slots`, ({ request, params }) => {
      if (!principal(request)) return unauthenticated();
      const url = new URL(request.url);
      const from = new Date(url.searchParams.get("from") ?? 0);
      const to = new Date(url.searchParams.get("to") ?? 0);
      const start = from > now() ? from : now();
      return HttpResponse.json(
        state.slots.filter(
          (s) =>
            s.clinician_id === params.id &&
            new Date(s.starts_at) >= start &&
            new Date(s.starts_at) < to &&
            !isBooked(state, s.id),
        ),
      );
    }),

    http.get(`${API}/appointments`, ({ request }) => {
      const user = principal(request);
      if (!user) return unauthenticated();
      if (user.role !== "patient") return forbidden();
      return HttpResponse.json(
        state.appointments
          .filter((a) => a.patient_id === user.subject)
          .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
          .map(publicView),
      );
    }),

    http.post(`${API}/appointments`, async ({ request }) => {
      const user = principal(request);
      if (!user) return unauthenticated();
      if (user.role !== "patient") return forbidden();
      const { slot_id: slotId } = (await request.json()) as { slot_id: string };
      const result = freeSlot(slotId);
      if (result.error) return result.error;
      const appt: DemoAppointment = {
        id: crypto.randomUUID(),
        patient_id: user.subject,
        clinician_id: result.slot.clinician_id,
        slot_id: result.slot.id,
        starts_at: result.slot.starts_at,
        ends_at: result.slot.ends_at,
        status: "booked",
        created_at: now().toISOString(),
        cancelled_at: null,
      };
      state.appointments.push(appt);
      return HttpResponse.json(publicView(appt), { status: 201 });
    }),

    http.post(`${API}/appointments/:id/cancel`, ({ request, params }) => {
      const user = principal(request);
      if (!user) return unauthenticated();
      const appt = ownAppointment(user, params.id);
      if (!appt) return notFound();
      const blocked = changeBlocked(appt);
      if (blocked) return blocked;
      appt.status = "cancelled";
      appt.cancelled_at = now().toISOString();
      return HttpResponse.json(publicView(appt));
    }),

    http.post(`${API}/appointments/:id/reschedule`, async ({ request, params }) => {
      const user = principal(request);
      if (!user) return unauthenticated();
      const appt = ownAppointment(user, params.id);
      if (!appt) return notFound();
      const blocked = changeBlocked(appt);
      if (blocked) return blocked;
      const { slot_id: slotId } = (await request.json()) as { slot_id: string };
      const result = freeSlot(slotId);
      if (result.error) return result.error;
      Object.assign(appt, {
        slot_id: result.slot.id,
        clinician_id: result.slot.clinician_id,
        starts_at: result.slot.starts_at,
        ends_at: result.slot.ends_at,
      });
      return HttpResponse.json(publicView(appt));
    }),

    http.get(`${API}/clinicians/me/schedule`, ({ request }) => {
      const user = principal(request);
      if (!user) return unauthenticated();
      if (user.role !== "clinician") return forbidden();
      const day = new URL(request.url).searchParams.get("day");
      return HttpResponse.json(
        state.appointments
          .filter(
            (a) =>
              a.clinician_id === user.subject &&
              a.status === "booked" &&
              dateInClinic(a.starts_at) === day,
          )
          .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
          .map(publicView),
      );
    }),
  ];
}

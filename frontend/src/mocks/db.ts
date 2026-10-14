/**
 * DEMO MODE ONLY - an in-browser stand-in for the CareSlot API so the UI can be shown to
 * clients without a server or database. All data is synthetic and lives in memory (a page
 * reload resets it, just as it signs the user out).
 *
 * The real business rules live in the backend (backend/src/careslot/modules/scheduling).
 * This file mirrors the user-visible ones - no double booking, 2-hour change cut-off,
 * ownership checks - so the demo behaves honestly. Types come from the OpenAPI contract, so
 * the mock cannot drift from the real API's shape without failing the type check.
 */
import type { Appointment, Clinic, ConsentPurpose, Role, Slot } from "@/api/types";

export const DEMO_TZ = "Europe/Helsinki";
export const CHANGE_CUTOFF_MS = 2 * 60 * 60 * 1000;

const CLINIC_ID = "0b6f4c64-0000-4000-8000-000000000001";
export const CLINICIANS = [
  {
    id: "c1000000-0000-4000-8000-000000000001",
    display_name: "Dr. Aava Example",
    specialty: "General practice",
  },
  {
    id: "c1000000-0000-4000-8000-000000000002",
    display_name: "Dr. Onni Sample",
    specialty: "Physiotherapy",
  },
] as const;

export type DemoUser = { subject: string; role: Role; display_name: string };

export const DEMO_USERS: Record<string, DemoUser> = {
  aino: {
    subject: "a1000000-0000-4000-8000-000000000001",
    role: "patient",
    display_name: "Aino (patient)",
  },
  eero: {
    subject: "a1000000-0000-4000-8000-000000000002",
    role: "patient",
    display_name: "Eero (patient)",
  },
  "dr.aava": { subject: CLINICIANS[0].id, role: "clinician", display_name: "Dr. Aava Example" },
  admin: { subject: "ad000000-0000-4000-8000-000000000001", role: "admin", display_name: "Admin" },
};

export const clinics: Clinic[] = [
  {
    id: CLINIC_ID,
    name: "Synthetic Health Centre",
    timezone: DEMO_TZ,
    clinicians: [...CLINICIANS],
  },
];

/** Milliseconds to add to a wall-clock time in `timeZone` to get UTC, at instant `utcMs`. */
function tzOffsetMs(utcMs: number, timeZone: string): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(new Date(utcMs));
  const get = (type: string) => Number(parts.find((p) => p.type === type)?.value);
  const asUtc = Date.UTC(
    get("year"),
    get("month") - 1,
    get("day"),
    get("hour"),
    get("minute"),
    get("second"),
  );
  return utcMs - asUtc;
}

/** Wall-clock time in the clinic timezone -> UTC Date (handles daylight saving). */
function clinicTime(year: number, month: number, day: number, hour: number, minute: number): Date {
  const guess = Date.UTC(year, month, day, hour, minute);
  return new Date(guess + tzOffsetMs(guess, DEMO_TZ));
}

function uuid(): string {
  return crypto.randomUUID();
}

function buildSlots(now: Date): Slot[] {
  const slots: Slot[] = [];
  for (let offset = 0; offset < 14; offset++) {
    const d = new Date(now);
    d.setDate(d.getDate() + offset);
    if (d.getDay() === 0 || d.getDay() === 6) continue;
    for (const clinician of CLINICIANS) {
      for (let minutes = 8 * 60; minutes < 16 * 60; minutes += 30) {
        const start = clinicTime(
          d.getFullYear(),
          d.getMonth(),
          d.getDate(),
          Math.floor(minutes / 60),
          minutes % 60,
        );
        slots.push({
          id: uuid(),
          clinician_id: clinician.id,
          starts_at: start.toISOString(),
          ends_at: new Date(start.getTime() + 30 * 60 * 1000).toISOString(),
        });
      }
    }
  }
  return slots;
}

export type DemoAppointment = Appointment & { patient_id: string };

export type DemoPatient = { id: string; full_name: string; identity_code: string | null };

export type DemoConsentDecision = {
  id: string;
  patient_id: string;
  purpose: ConsentPurpose;
  granted: boolean;
  decided_at: string;
  policy_version: string;
};

export const CONSENT_PURPOSES: ConsentPurpose[] = [
  "regional-record-sharing",
  "research",
  "ai-summaries",
];
export const POLICY_VERSION = "2026-01";

export type DemoState = {
  slots: Slot[];
  appointments: DemoAppointment[];
  patients: DemoPatient[];
  consents: DemoConsentDecision[];
};

/** Same synthetic people as backend/src/careslot/seed.py (identity codes in the 900-999 range). */
function demoPatients(): DemoPatient[] {
  return [
    { id: DEMO_USERS.aino?.subject ?? "", full_name: "Aino Example", identity_code: "150385-9013" },
    { id: DEMO_USERS.eero?.subject ?? "", full_name: "Eero Sample", identity_code: "020794-9029" },
  ];
}

export function createDemoState(now = new Date()): DemoState {
  const slots = buildSlots(now);
  const state: DemoState = { slots, appointments: [], patients: demoPatients(), consents: [] };

  // Pre-book a few future slots so the clinician's day and Aino's list are not empty.
  const future = slots.filter(
    (s) => new Date(s.starts_at).getTime() > now.getTime() + 24 * 3600 * 1000,
  );
  const patients = [DEMO_USERS.aino, DEMO_USERS.eero];
  future
    .filter((s) => s.clinician_id === CLINICIANS[0].id)
    .slice(0, 6)
    .forEach((slot, i) => {
      const patient = patients[i % 2];
      if (!patient || i % 3 === 2) return; // leave gaps
      state.appointments.push({
        id: uuid(),
        patient_id: patient.subject,
        clinician_id: slot.clinician_id,
        slot_id: slot.id,
        starts_at: slot.starts_at,
        ends_at: slot.ends_at,
        status: "booked",
        created_at: now.toISOString(),
        cancelled_at: null,
        cancellation_reason: null,
      });
    });
  return state;
}

export function isBooked(state: DemoState, slotId: string): boolean {
  return state.appointments.some((a) => a.slot_id === slotId && a.status === "booked");
}

export function dateInClinic(iso: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: DEMO_TZ }).format(new Date(iso));
}

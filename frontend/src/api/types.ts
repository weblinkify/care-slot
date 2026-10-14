/**
 * Friendly aliases for the generated OpenAPI types (`npm run gen:api`). Components import
 * from here, never from schema.d.ts directly, so a regenerated schema touches one file.
 */
import type { components } from "./schema";

type Schemas = components["schemas"];

export type Appointment = Schemas["AppointmentOut"];
export type Clinic = Schemas["ClinicOut"];
export type Clinician = Schemas["ClinicianOut"];
export type Slot = Schemas["SlotOut"];
export type TokenResponse = Schemas["TokenResponse"];
export type Role = Schemas["Role"];

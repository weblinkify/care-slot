/**
 * Date/time formatting. Times are always shown in the clinic's timezone (not the browser's):
 * a patient travelling abroad must still see the local time of their appointment.
 */
export const CLINIC_TZ = "Europe/Helsinki";
const LOCALE = "en-GB";

export function formatTime(iso: string, timeZone = CLINIC_TZ): string {
  return new Intl.DateTimeFormat(LOCALE, { timeZone, hour: "2-digit", minute: "2-digit" }).format(
    new Date(iso),
  );
}

export function formatDateTime(iso: string, timeZone = CLINIC_TZ): string {
  return new Intl.DateTimeFormat(LOCALE, {
    timeZone,
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

/** `YYYY-MM-DD` of the next weekday (today if it is a weekday). */
export function nextWeekday(from = new Date()): string {
  const d = new Date(from);
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
  return toIsoDate(d);
}

export function toIsoDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${String(d.getFullYear())}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** UTC window covering one calendar day in the clinic timezone (wide enough for any offset). */
export function dayWindow(isoDate: string): { from: string; to: string } {
  const start = new Date(`${isoDate}T00:00:00Z`);
  start.setUTCHours(start.getUTCHours() - 14);
  const end = new Date(`${isoDate}T00:00:00Z`);
  end.setUTCHours(end.getUTCHours() + 38);
  return { from: start.toISOString(), to: end.toISOString() };
}

export function isoDateInClinic(iso: string, timeZone = CLINIC_TZ): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(new Date(iso));
}

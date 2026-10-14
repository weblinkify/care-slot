import { useState } from "react";
import { Link } from "react-router";

import { ApiError } from "@/api/client";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field, Select } from "@/components/ui/Field";
import { Spinner } from "@/components/ui/Spinner";
import { formatDateTime, formatTime, nextWeekday } from "@/lib/format";

import { useBook, useClinics, useSlots } from "./api";
import { SlotPicker } from "./SlotPicker";

export function BookingPage() {
  const clinics = useClinics();
  const clinicians = clinics.data?.flatMap((c) => c.clinicians) ?? [];
  const [clinicianId, setClinicianId] = useState<string>("");
  const [day, setDay] = useState(nextWeekday);
  const [slotId, setSlotId] = useState<string | null>(null);

  const activeClinicianId = clinicianId || clinicians[0]?.id;
  const slots = useSlots(activeClinicianId, day);
  const book = useBook();

  const clinician = clinicians.find((c) => c.id === activeClinicianId);
  const slot = slots.data?.find((s) => s.id === slotId);

  if (clinics.isLoading) return <Spinner label="Loading clinics" />;
  if (clinics.error) return <Alert tone="danger">Could not load clinics.</Alert>;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Book an appointment</h1>
        <p className="mt-1 text-sm text-ink-muted">
          {clinics.data?.[0]?.name}. Times are shown in clinic time.
        </p>
      </header>

      {book.isSuccess && (
        <Alert tone="success">
          Booked for {formatDateTime(book.data.starts_at)}.{" "}
          <Link to="/appointments" className="font-medium text-brand underline underline-offset-2">
            View my appointments
          </Link>
        </Alert>
      )}
      {book.error && (
        <Alert tone="danger">
          {book.error instanceof ApiError ? book.error.message : "Booking failed."}
        </Alert>
      )}

      <Card className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Clinician">
            {({ id, className }) => (
              <Select
                id={id}
                className={className}
                value={activeClinicianId ?? ""}
                onChange={(e) => {
                  setClinicianId(e.target.value);
                  setSlotId(null);
                }}
              >
                {clinicians.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.display_name} - {c.specialty}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label="Date">
            {({ id, className }) => (
              <input
                id={id}
                type="date"
                className={className}
                value={day}
                onChange={(e) => {
                  setDay(e.target.value);
                  setSlotId(null);
                }}
              />
            )}
          </Field>
        </div>

        <SlotPicker
          name="slot"
          slots={slots.data}
          isLoading={slots.isLoading}
          selected={slotId}
          onSelect={setSlotId}
        />

        <div className="flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-ink-muted" aria-live="polite">
            {slot && clinician
              ? `${clinician.display_name}, ${formatTime(slot.starts_at)}`
              : "Choose a time to continue."}
          </p>
          <Button
            disabled={!slotId || book.isPending}
            onClick={() => {
              if (slotId)
                book.mutate(slotId, {
                  onSuccess: () => {
                    setSlotId(null);
                  },
                });
            }}
          >
            {book.isPending ? "Booking..." : "Book appointment"}
          </Button>
        </div>
      </Card>
    </div>
  );
}

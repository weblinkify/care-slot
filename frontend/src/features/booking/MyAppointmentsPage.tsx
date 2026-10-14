import { useState } from "react";

import { ApiError } from "@/api/client";
import type { Appointment } from "@/api/types";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Spinner } from "@/components/ui/Spinner";
import { cn } from "@/lib/cn";
import { formatDateTime, isoDateInClinic } from "@/lib/format";

import { useCancel, useMyAppointments, useReschedule, useSlots } from "./api";
import { SlotPicker } from "./SlotPicker";

export function MyAppointmentsPage() {
  const appointments = useMyAppointments();
  const cancel = useCancel();
  const [rescheduling, setRescheduling] = useState<string | null>(null);

  if (appointments.isLoading) return <Spinner label="Loading appointments" />;
  if (appointments.error) return <Alert tone="danger">Could not load appointments.</Alert>;

  const items = appointments.data ?? [];
  const mutationError = cancel.error;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">My appointments</h1>

      {mutationError && (
        <Alert tone="danger">
          {mutationError instanceof ApiError ? mutationError.message : "Something went wrong."}
        </Alert>
      )}

      {items.length === 0 ? (
        <Alert>You have no appointments yet.</Alert>
      ) : (
        <ul className="space-y-3">
          {items.map((appt) => (
            <li key={appt.id}>
              <Card className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium tabular-nums">{formatDateTime(appt.starts_at)}</p>
                    <StatusBadge status={appt.status} />
                  </div>
                  {appt.status === "booked" && (
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        aria-expanded={rescheduling === appt.id}
                        onClick={() => {
                          setRescheduling(rescheduling === appt.id ? null : appt.id);
                        }}
                      >
                        Reschedule
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={cancel.isPending}
                        onClick={() => {
                          cancel.mutate(appt.id);
                        }}
                      >
                        Cancel
                        <span className="sr-only">
                          {" "}
                          appointment on {formatDateTime(appt.starts_at)}
                        </span>
                      </Button>
                    </div>
                  )}
                </div>
                {rescheduling === appt.id && (
                  <ReschedulePanel
                    appointment={appt}
                    onDone={() => {
                      setRescheduling(null);
                    }}
                  />
                )}
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: Appointment["status"] }) {
  return (
    <span
      className={cn(
        "mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize",
        status === "booked" ? "bg-success-soft text-success" : "bg-surface-muted text-ink-muted",
      )}
    >
      {status}
    </span>
  );
}

function ReschedulePanel({
  appointment,
  onDone,
}: {
  appointment: Appointment;
  onDone: () => void;
}) {
  const [day, setDay] = useState(() => isoDateInClinic(appointment.starts_at));
  const [slotId, setSlotId] = useState<string | null>(null);
  const slots = useSlots(appointment.clinician_id, day);
  const reschedule = useReschedule();

  return (
    <div className="space-y-4 rounded-control bg-surface-muted p-4">
      <Field label="New date">
        {({ id, className }) => (
          <input
            id={id}
            type="date"
            className={cn(className, "sm:max-w-48")}
            value={day}
            onChange={(e) => {
              setDay(e.target.value);
              setSlotId(null);
            }}
          />
        )}
      </Field>
      <SlotPicker
        name={`reschedule-${appointment.id}`}
        slots={slots.data}
        isLoading={slots.isLoading}
        selected={slotId}
        onSelect={setSlotId}
      />
      {reschedule.error && (
        <Alert tone="danger">
          {reschedule.error instanceof ApiError
            ? reschedule.error.message
            : "Could not reschedule."}
        </Alert>
      )}
      <Button
        disabled={!slotId || reschedule.isPending}
        onClick={() => {
          if (slotId)
            reschedule.mutate({ appointmentId: appointment.id, slotId }, { onSuccess: onDone });
        }}
      >
        Confirm new time
      </Button>
    </div>
  );
}

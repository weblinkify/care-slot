import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import type { Appointment } from "@/api/types";
import { Alert } from "@/components/ui/Alert";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Spinner } from "@/components/ui/Spinner";
import { cn } from "@/lib/cn";
import { formatTime, nextWeekday } from "@/lib/format";

export function SchedulePage() {
  const [day, setDay] = useState(nextWeekday);
  const schedule = useQuery({
    queryKey: ["schedule", day],
    queryFn: () => api<Appointment[]>(`/clinicians/me/schedule?day=${day}`),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">My day</h1>
        <Field label="Day">
          {({ id, className }) => (
            <input
              id={id}
              type="date"
              className={cn(className, "w-44")}
              value={day}
              onChange={(e) => {
                setDay(e.target.value);
              }}
            />
          )}
        </Field>
      </div>

      {schedule.isLoading && <Spinner label="Loading schedule" />}
      {schedule.error && <Alert tone="danger">Could not load the schedule.</Alert>}
      {schedule.data?.length === 0 && <Alert>No appointments on this day.</Alert>}

      {!!schedule.data?.length && (
        <Card className="p-0">
          <ol className="divide-y divide-line">
            {schedule.data.map((appt) => (
              <li key={appt.id} className="flex items-center gap-4 px-5 py-3">
                <span className="w-24 font-medium tabular-nums">
                  {formatTime(appt.starts_at)}-{formatTime(appt.ends_at)}
                </span>
                {/* Patient identity is deliberately not shown here: the clinician opens the
                    patient record explicitly, which is an audited access (milestone 3). */}
                <span className="text-sm text-ink-muted">Appointment {appt.id.slice(0, 8)}</span>
              </li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, api } from "@/api/client";
import type { AccessReason, PatientSummary } from "@/api/types";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field, Select } from "@/components/ui/Field";

const CLINICAL_REASONS: { value: AccessReason; label: string }[] = [
  { value: "appointment-preparation", label: "Preparing for the appointment" },
  { value: "treatment", label: "Treatment" },
];

/**
 * Opening a record is a deliberate act: the clinician states a purpose, the API checks the
 * care relationship, and the access is written to the audit log with that purpose. The data
 * is fetched on demand (a mutation, not a cached query) so it is never loaded "just in case".
 */
export function OpenPatientRecord({ patientId }: { patientId: string }) {
  const [reason, setReason] = useState<AccessReason>("appointment-preparation");
  const open = useMutation({
    mutationFn: () =>
      api<PatientSummary>(`/patients/${patientId}?reason=${encodeURIComponent(reason)}`),
  });

  if (open.data) {
    return (
      <div className="rounded-control bg-surface-muted px-4 py-3 text-sm">
        <p className="font-medium">{open.data.full_name}</p>
        <p className="text-ink-muted tabular-nums">{open.data.identity_code_masked ?? "-"}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-control bg-surface-muted p-3">
      <div className="min-w-56 flex-1">
        <Field label="Reason for access" hint="Recorded in the audit log.">
          {({ id, className, describedBy }) => (
            <Select
              id={id}
              className={className}
              aria-describedby={describedBy}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value as AccessReason);
              }}
            >
              {CLINICAL_REASONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
      <Button
        variant="secondary"
        disabled={open.isPending}
        onClick={() => {
          open.mutate();
        }}
      >
        Open record
      </Button>
      {open.error && (
        <Alert tone="danger" className="w-full">
          {open.error instanceof ApiError ? open.error.message : "Could not open the record."}
        </Alert>
      )}
    </div>
  );
}

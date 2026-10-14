import { Alert } from "@/components/ui/Alert";
import { Card, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";

import { useOwnRecord } from "./api";

/** GDPR right of access: the patient sees everything the service stores about them. */
export function ProfilePage() {
  const record = useOwnRecord();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">My data</h1>
        <p className="mt-1 text-sm text-ink-muted">
          This is everything CareSlot stores about you, apart from your appointments.
        </p>
      </header>

      {record.isLoading && <Spinner label="Loading your data" />}
      {record.error && <Alert tone="danger">Could not load your data.</Alert>}
      {record.data && (
        <Card>
          <CardTitle>Personal details</CardTitle>
          <dl className="mt-4 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[max-content_1fr]">
            <dt className="text-ink-muted">Name</dt>
            <dd className="font-medium">{record.data.full_name}</dd>
            <dt className="text-ink-muted">Personal identity code</dt>
            <dd className="font-medium tabular-nums">{record.data.identity_code ?? "-"}</dd>
          </dl>
          <p className="mt-4 text-xs text-ink-muted">
            Your identity code is stored encrypted. Clinicians only ever see its first part.
          </p>
        </Card>
      )}
    </div>
  );
}

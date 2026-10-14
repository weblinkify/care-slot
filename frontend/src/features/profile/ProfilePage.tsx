import { useId, useState } from "react";
import { useNavigate } from "react-router";

import { ApiError } from "@/api/client";
import type { ConsentPurpose } from "@/api/types";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Switch } from "@/components/ui/Switch";
import { useAuth } from "@/features/auth/session";
import { formatDateTime } from "@/lib/format";

import { useConsents, useDecideConsent, useEraseMe, useOwnRecord } from "./api";

const PURPOSES: Record<ConsentPurpose, { title: string; description: string }> = {
  "regional-record-sharing": {
    title: "Share with the regional health record",
    description: "Other healthcare providers in your region can see your appointment history.",
  },
  research: {
    title: "Research use",
    description: "Pseudonymised appointment data may be included in approved research extracts.",
  },
  "ai-summaries": {
    title: "AI-assisted day summaries",
    description:
      "Your appointments may be included, without your name or identity code, in AI-generated summaries that help your clinician plan their day.",
  },
};

/** GDPR in one place: right of access, consent management, right to erasure. */
export function ProfilePage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">My data</h1>
        <p className="mt-1 text-sm text-ink-muted">
          What CareSlot stores about you, what you allow it to be used for, and how to remove it.
        </p>
      </header>
      <PersonalDetails />
      <Consents />
      <Erasure />
    </div>
  );
}

function PersonalDetails() {
  const record = useOwnRecord();
  if (record.isLoading) return <Spinner label="Loading your data" />;
  if (record.error || !record.data) return <Alert tone="danger">Could not load your data.</Alert>;

  return (
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
  );
}

function Consents() {
  const consents = useConsents();
  const decide = useDecideConsent();
  const headingId = useId();

  return (
    <Card aria-labelledby={headingId}>
      <CardTitle id={headingId}>Consents</CardTitle>
      <p className="mt-1 text-sm text-ink-muted">
        Nothing is shared unless you switch it on. You can change your mind at any time.
      </p>

      {consents.isLoading && <Spinner label="Loading consents" className="mt-4" />}
      {decide.error && (
        <Alert tone="danger" className="mt-4">
          {decide.error instanceof ApiError ? decide.error.message : "Could not save your choice."}
        </Alert>
      )}

      {consents.data && (
        <>
          <ul className="mt-4 divide-y divide-line">
            {consents.data.current.map((c) => {
              const copy = PURPOSES[c.purpose];
              const labelId = `${headingId}-${c.purpose}`;
              return (
                <li key={c.purpose} className="flex items-start justify-between gap-6 py-4">
                  <div>
                    <p id={labelId} className="text-sm font-medium">
                      {copy.title}
                    </p>
                    <p className="mt-0.5 text-sm text-ink-muted">{copy.description}</p>
                  </div>
                  <Switch
                    aria-labelledby={labelId}
                    checked={c.granted}
                    disabled={decide.isPending}
                    onCheckedChange={(granted) => {
                      decide.mutate({ purpose: c.purpose, granted });
                    }}
                  />
                </li>
              );
            })}
          </ul>

          {consents.data.history.length > 0 && (
            <details className="group mt-2 text-sm">
              <summary className="cursor-pointer font-medium text-brand">
                Consent history ({consents.data.history.length})
              </summary>
              <ol className="mt-3 space-y-1.5 text-ink-muted">
                {consents.data.history.map((h) => (
                  <li key={h.id} className="tabular-nums">
                    {formatDateTime(h.decided_at)}: {h.granted ? "granted" : "withdrawn"}{" "}
                    <span className="text-ink">{PURPOSES[h.purpose].title}</span> (notice version{" "}
                    {h.policy_version})
                  </li>
                ))}
              </ol>
            </details>
          )}
        </>
      )}
    </Card>
  );
}

function Erasure() {
  const [understood, setUnderstood] = useState(false);
  const erase = useEraseMe();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const checkboxId = useId();

  return (
    <Card className="border-danger/40">
      <CardTitle>Delete my data</CardTitle>
      <p className="mt-1 text-sm text-ink-muted">
        Removes your name and identity code and cancels your upcoming appointments. A record that
        your data was accessed is kept without your identity, as the law requires. This cannot be
        undone.
      </p>

      {erase.error && (
        <Alert tone="danger" className="mt-4">
          {erase.error instanceof ApiError ? erase.error.message : "Could not delete your data."}
        </Alert>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
        <label htmlFor={checkboxId} className="flex items-center gap-2 text-sm">
          <input
            id={checkboxId}
            type="checkbox"
            checked={understood}
            onChange={(e) => {
              setUnderstood(e.target.checked);
            }}
            className="size-4 accent-danger"
          />
          I understand this is permanent
        </label>
        <Button
          variant="danger"
          disabled={!understood || erase.isPending}
          onClick={() => {
            erase.mutate(undefined, {
              onSuccess: () => {
                logout();
                void navigate("/login?erased=1", { replace: true });
              },
            });
          }}
        >
          {erase.isPending ? "Deleting..." : "Delete my data"}
        </Button>
      </div>
    </Card>
  );
}

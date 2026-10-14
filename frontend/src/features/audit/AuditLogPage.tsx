import { useInfiniteQuery, useMutation } from "@tanstack/react-query";
import { useState, type SubmitEvent } from "react";

import { api } from "@/api/client";
import type { AuditEntry, ChainVerification } from "@/api/types";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Spinner } from "@/components/ui/Spinner";
import { formatDateTime } from "@/lib/format";

const PAGE_SIZE = 25;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function useAuditLog(patientId: string) {
  return useInfiniteQuery({
    queryKey: ["audit-log", patientId],
    initialPageParam: undefined as number | undefined,
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
      if (patientId) params.set("patient_id", patientId);
      if (pageParam) params.set("before_id", String(pageParam));
      return api<AuditEntry[]>(`/audit-log?${params.toString()}`);
    },
    // Keyset pagination: the next page starts below the last id we have seen.
    getNextPageParam: (last) => (last.length === PAGE_SIZE ? last.at(-1)?.id : undefined),
  });
}

const short = (id: string | null) => (id ? id.slice(0, 8) : "system");

export function AuditLogPage() {
  const [filterInput, setFilterInput] = useState("");
  const [patientId, setPatientId] = useState("");
  const log = useAuditLog(patientId);
  const verify = useMutation({ mutationFn: () => api<ChainVerification>("/audit-log/verify") });

  const filterError =
    filterInput && !UUID_PATTERN.test(filterInput) ? "Enter a full patient id (UUID)." : undefined;

  function onFilter(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!filterError) setPatientId(filterInput.trim());
  }

  const entries = log.data?.pages.flat() ?? [];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Audit log</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Every access to patient data. Append-only and hash-chained; your searches are logged
            too.
          </p>
        </div>
        <Button
          variant="secondary"
          disabled={verify.isPending}
          onClick={() => {
            verify.mutate();
          }}
        >
          {verify.isPending ? "Verifying..." : "Verify integrity"}
        </Button>
      </header>

      {verify.data && (
        <Alert tone={verify.data.valid ? "success" : "danger"}>
          {verify.data.valid
            ? `Chain intact: ${String(verify.data.entries_checked)} entries verified.`
            : `Tampering detected at entry #${String(verify.data.first_invalid_id)} (${String(verify.data.entries_checked)} entries verified before it).`}
        </Alert>
      )}

      <form onSubmit={onFilter} className="flex flex-wrap items-end gap-3" noValidate>
        <div className="min-w-72 flex-1">
          <Field label="Filter by patient id" error={filterError}>
            {({ id, className, describedBy, invalid }) => (
              <input
                id={id}
                className={className}
                aria-describedby={describedBy}
                aria-invalid={invalid}
                placeholder="e.g. a1000000-0000-4000-8000-000000000001"
                value={filterInput}
                onChange={(e) => {
                  setFilterInput(e.target.value);
                }}
              />
            )}
          </Field>
        </div>
        <Button type="submit" variant="secondary">
          Apply
        </Button>
        {patientId && (
          <Button
            variant="ghost"
            onClick={() => {
              setFilterInput("");
              setPatientId("");
            }}
          >
            Clear
          </Button>
        )}
      </form>

      {log.isLoading && <Spinner label="Loading audit log" />}
      {log.error && <Alert tone="danger">Could not load the audit log.</Alert>}

      {log.data && (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Audit entries, newest first</caption>
              <thead className="border-b border-line bg-surface-muted text-xs tracking-wide text-ink-muted uppercase">
                <tr>
                  {["#", "When", "Actor", "Action", "Patient", "Reason"].map((h) => (
                    <th key={h} scope="col" className="px-4 py-2.5 font-medium whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {entries.map((e) => (
                  <tr key={e.id} className="hover:bg-surface-muted">
                    <td className="px-4 py-2.5 text-ink-muted tabular-nums">{e.id}</td>
                    <td className="px-4 py-2.5 whitespace-nowrap tabular-nums">
                      {formatDateTime(e.occurred_at)}
                    </td>
                    <td className="px-4 py-2.5 whitespace-nowrap">
                      <span className="font-mono text-xs">{short(e.actor_id)}</span>{" "}
                      <span className="text-ink-muted">{e.actor_role ?? ""}</span>
                    </td>
                    <td className="px-4 py-2.5 font-medium whitespace-nowrap">{e.action}</td>
                    <td className="px-4 py-2.5 font-mono text-xs">{short(e.patient_id)}</td>
                    <td className="px-4 py-2.5 whitespace-nowrap text-ink-muted">{e.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {entries.length === 0 && <p className="px-4 py-6 text-sm text-ink-muted">No entries.</p>}
        </Card>
      )}

      {log.hasNextPage && (
        <Button
          variant="secondary"
          disabled={log.isFetchingNextPage}
          onClick={() => {
            void log.fetchNextPage();
          }}
        >
          {log.isFetchingNextPage ? "Loading..." : "Load older entries"}
        </Button>
      )}
    </div>
  );
}

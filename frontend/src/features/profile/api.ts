import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { OwnPatientRecord } from "@/api/types";

export const profileKey = ["patients", "me"] as const;

export function useOwnRecord() {
  return useQuery({ queryKey: profileKey, queryFn: () => api<OwnPatientRecord>("/patients/me") });
}

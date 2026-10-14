import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import type {
  ConsentOverview,
  ConsentPurpose,
  ConsentState,
  ErasureResult,
  OwnPatientRecord,
} from "@/api/types";

export const profileKey = ["patients", "me"] as const;
export const consentKey = ["consents"] as const;

export function useOwnRecord() {
  return useQuery({ queryKey: profileKey, queryFn: () => api<OwnPatientRecord>("/patients/me") });
}

export function useConsents() {
  return useQuery({ queryKey: consentKey, queryFn: () => api<ConsentOverview>("/consents") });
}

export function useDecideConsent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ purpose, granted }: { purpose: ConsentPurpose; granted: boolean }) =>
      api<ConsentState>(`/consents/${purpose}`, {
        method: "PUT",
        body: JSON.stringify({ granted }),
      }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: consentKey }),
  });
}

export function useEraseMe() {
  return useMutation({
    mutationFn: () =>
      api<ErasureResult>("/patients/me/erasure", {
        method: "POST",
        body: JSON.stringify({ confirm: true }),
      }),
  });
}

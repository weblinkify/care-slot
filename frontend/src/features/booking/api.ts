import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { Appointment, Clinic, Slot } from "@/api/types";
import { dayWindow, isoDateInClinic } from "@/lib/format";

/** Query keys in one place so invalidation after a mutation cannot miss a cache entry. */
export const keys = {
  clinics: ["clinics"] as const,
  slots: (clinicianId: string, day: string) => ["slots", clinicianId, day] as const,
  allSlots: ["slots"] as const,
  myAppointments: ["appointments", "mine"] as const,
};

export function useClinics() {
  return useQuery({ queryKey: keys.clinics, queryFn: () => api<Clinic[]>("/clinics") });
}

export function useSlots(clinicianId: string | undefined, day: string) {
  return useQuery({
    queryKey: keys.slots(clinicianId ?? "", day),
    enabled: Boolean(clinicianId),
    queryFn: async () => {
      const { from, to } = dayWindow(day);
      const params = new URLSearchParams({ from, to });
      const slots = await api<Slot[]>(
        `/clinicians/${clinicianId ?? ""}/slots?${params.toString()}`,
      );
      return slots.filter((s) => isoDateInClinic(s.starts_at) === day);
    },
  });
}

export function useMyAppointments() {
  return useQuery({
    queryKey: keys.myAppointments,
    queryFn: () => api<Appointment[]>("/appointments"),
  });
}

function useInvalidateBookingData() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: keys.myAppointments }),
      queryClient.invalidateQueries({ queryKey: keys.allSlots }),
    ]);
}

export function useBook() {
  const invalidate = useInvalidateBookingData();
  return useMutation({
    mutationFn: (slotId: string) =>
      api<Appointment>("/appointments", {
        method: "POST",
        body: JSON.stringify({ slot_id: slotId }),
      }),
    onSettled: invalidate, // also on error: a 409 means our slot list is stale
  });
}

export function useCancel() {
  const invalidate = useInvalidateBookingData();
  return useMutation({
    mutationFn: (appointmentId: string) =>
      api<Appointment>(`/appointments/${appointmentId}/cancel`, { method: "POST" }),
    onSettled: invalidate,
  });
}

export function useReschedule() {
  const invalidate = useInvalidateBookingData();
  return useMutation({
    mutationFn: ({ appointmentId, slotId }: { appointmentId: string; slotId: string }) =>
      api<Appointment>(`/appointments/${appointmentId}/reschedule`, {
        method: "POST",
        body: JSON.stringify({ slot_id: slotId }),
      }),
    onSettled: invalidate,
  });
}

/**
 * DEMO MODE ONLY - in-browser audit log with the same SHA-256 hash chain as the backend
 * (backend/src/careslot/modules/audit/domain/model.py), so "Verify integrity" in the demo
 * performs a real verification rather than returning a canned answer.
 */
import type { AccessReason, AuditEntry, ChainVerification } from "@/api/types";

import type { DemoUser } from "./db";

const GENESIS = "0".repeat(64);

type Draft = Omit<AuditEntry, "id" | "hash">;

async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

function canonical(e: Draft): string {
  const {
    occurred_at,
    actor_id,
    actor_role,
    action,
    resource_type,
    resource_id,
    patient_id,
    reason,
  } = e;
  // Keys sorted, like the backend's json.dumps(sort_keys=True).
  return JSON.stringify({
    action,
    actor_id,
    actor_role,
    occurred_at,
    patient_id,
    reason,
    resource_id,
    resource_type,
  });
}

export class DemoAuditLog {
  private entries: (AuditEntry & { prev_hash: string })[] = [];
  private tail: Promise<void> = Promise.resolve();

  record(
    actor: DemoUser | null,
    action: string,
    resourceType: string,
    resourceId: string,
    patientId: string | null,
    reason: AccessReason,
  ): Promise<void> {
    // Appends are chained one after another, like the backend's advisory lock.
    this.tail = this.tail.then(async () => {
      const prev = this.entries.at(-1)?.hash ?? GENESIS;
      const draft: Draft = {
        occurred_at: new Date().toISOString(),
        actor_id: actor?.subject ?? null,
        actor_role: actor?.role ?? null,
        action,
        resource_type: resourceType,
        resource_id: resourceId,
        patient_id: patientId,
        reason,
      };
      const hash = await sha256Hex(prev + canonical(draft));
      this.entries.push({ ...draft, id: this.entries.length + 1, hash, prev_hash: prev });
    });
    return this.tail;
  }

  search(patientId: string | null, beforeId: number | null, limit: number): AuditEntry[] {
    return this.entries
      .filter((e) => (!patientId || e.patient_id === patientId) && (!beforeId || e.id < beforeId))
      .reverse()
      .slice(0, limit)
      .map(({ prev_hash, ...entry }) => entry);
  }

  async verify(): Promise<ChainVerification> {
    await this.tail;
    let prev = GENESIS;
    for (const [index, e] of this.entries.entries()) {
      if (e.prev_hash !== prev || (await sha256Hex(prev + canonical(e))) !== e.hash) {
        return { valid: false, entries_checked: index, first_invalid_id: e.id };
      }
      prev = e.hash;
    }
    return { valid: true, entries_checked: this.entries.length, first_invalid_id: null };
  }
}

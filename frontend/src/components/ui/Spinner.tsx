import { cn } from "@/lib/cn";

export function Spinner({ label = "Loading", className }: { label?: string; className?: string }) {
  return (
    <span
      role="status"
      className={cn("inline-flex items-center gap-2 text-sm text-ink-muted", className)}
    >
      <span
        aria-hidden="true"
        className="size-4 animate-spin rounded-full border-2 border-line border-t-brand motion-reduce:animate-none"
      />
      <span className="sr-only">{label}</span>
    </span>
  );
}

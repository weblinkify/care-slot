import { useId, type ComponentProps, type ReactNode } from "react";

import { cn } from "@/lib/cn";

const controlClasses =
  "block w-full rounded-control border border-line bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-muted aria-invalid:border-danger";

type FieldProps = {
  label: string;
  hint?: string;
  error?: string | undefined;
  children: (control: {
    id: string;
    className: string;
    describedBy?: string;
    invalid: boolean;
  }) => ReactNode;
};

/**
 * Accessible form field: wires label, hint and error to the control with ids so screen
 * readers announce them. Renders the control through a render prop so the same wiring works
 * for <input>, <select> and <textarea>.
 */
export function Field({ label, hint, error, children }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
      </label>
      {children({
        id,
        className: controlClasses,
        invalid: Boolean(error),
        ...(describedBy ? { describedBy } : {}),
      })}
      {hint && (
        <p id={hintId} className="text-xs text-ink-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

export function Select({ className, ...props }: ComponentProps<"select">) {
  return <select className={cn(controlClasses, className)} {...props} />;
}

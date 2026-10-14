import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

type SwitchProps = Omit<ComponentProps<"button">, "onChange" | "role"> & {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
};

/**
 * Accessible on/off switch: a real <button role="switch"> with aria-checked, so it is
 * keyboard-operable (Space/Enter) and announced as "switch, on/off". All visual state comes
 * from Tailwind's aria-checked: variants - one source of truth for state and style.
 */
export function Switch({ checked, onCheckedChange, className, ...props }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => {
        onCheckedChange(!checked);
      }}
      className={cn(
        "group relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border-2 border-transparent bg-line transition-colors disabled:cursor-not-allowed disabled:opacity-50 aria-checked:bg-brand motion-reduce:transition-none",
        className,
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className="inline-block size-5 translate-x-0 rounded-full bg-surface shadow-sm transition-transform group-aria-checked:translate-x-5 motion-reduce:transition-none"
      />
    </button>
  );
}

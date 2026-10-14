import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

const alertVariants = cva("rounded-control border px-4 py-3 text-sm", {
  variants: {
    tone: {
      info: "border-line bg-surface-muted text-ink",
      success: "border-success/30 bg-success-soft text-ink",
      danger: "border-danger/30 bg-danger-soft text-ink",
    },
  },
  defaultVariants: { tone: "info" },
});

type AlertProps = ComponentProps<"div"> & VariantProps<typeof alertVariants>;

/**
 * Errors use role="alert" (announced immediately); other tones use role="status"
 * (announced politely) so screen-reader users are not interrupted by non-urgent messages.
 */
export function Alert({ className, tone, ...props }: AlertProps) {
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn(alertVariants({ tone }), className)}
      {...props}
    />
  );
}

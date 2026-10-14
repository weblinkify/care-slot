import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Compose Tailwind classes. `twMerge` resolves conflicts so a caller's `className="px-6"`
 * reliably overrides a component's default `px-4` instead of depending on CSS source order.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

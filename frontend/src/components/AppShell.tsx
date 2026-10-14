import type { ReactNode } from "react";

/**
 * Page chrome: skip link, banner, main landmark. Landmarks let screen-reader and keyboard
 * users jump straight to content; the skip link is the first focusable element on every page.
 */
export function AppShell({ nav, children }: { nav?: ReactNode; children: ReactNode }) {
  return (
    <div className="min-h-dvh">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-control focus:bg-surface focus:px-4 focus:py-2 focus:shadow-md"
      >
        Skip to content
      </a>
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between gap-4 px-4">
          <span className="flex items-center gap-2 font-semibold">
            <img src="/favicon.svg" alt="" className="size-6" />
            CareSlot
          </span>
          {nav}
        </div>
      </header>
      <main id="main" tabIndex={-1} className="mx-auto max-w-5xl px-4 py-8 focus:outline-none">
        {children}
      </main>
    </div>
  );
}

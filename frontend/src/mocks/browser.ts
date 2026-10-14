/** DEMO MODE ONLY - starts the in-browser mock API. Loaded via dynamic import from main.tsx,
 * so neither MSW nor the synthetic data ends up in the normal production bundle. */
import { setupWorker } from "msw/browser";

import { createHandlers } from "./handlers";

export async function startDemoApi(): Promise<void> {
  await setupWorker(...createHandlers()).start({
    onUnhandledFrame: "bypass", // assets, fonts etc. go to the network as normal
    quiet: true,
  });
}

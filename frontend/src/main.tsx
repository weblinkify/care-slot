import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/App";
import { ApiError } from "@/api/client";
import { AuthProvider } from "@/features/auth/AuthProvider";

import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Client errors (4xx) will not fix themselves on retry; only retry transient failures.
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
      staleTime: 30_000,
    },
  },
});

const root = document.getElementById("root");
if (!root) throw new Error("#root element missing");

if (import.meta.env.VITE_DEMO_MODE === "true") {
  // Client demo build: the API runs in the browser on synthetic data (see src/mocks).
  const { startDemoApi } = await import("./mocks/browser");
  await startDemoApi();
}

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);

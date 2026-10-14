import { createBrowserRouter, Navigate, NavLink, Outlet, RouterProvider } from "react-router";

import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/Button";
import { Card, CardTitle } from "@/components/ui/Card";
import { HOME_BY_ROLE, useAuth } from "@/features/auth/session";
import { LoginPage } from "@/features/auth/LoginPage";
import { RequireRole } from "@/features/auth/RequireRole";
import { BookingPage } from "@/features/booking/BookingPage";
import { MyAppointmentsPage } from "@/features/booking/MyAppointmentsPage";
import { SchedulePage } from "@/features/schedule/SchedulePage";
import { cn } from "@/lib/cn";

const NAV = {
  patient: [
    { to: "/book", label: "Book" },
    { to: "/appointments", label: "My appointments" },
  ],
  clinician: [{ to: "/schedule", label: "My day" }],
  admin: [{ to: "/admin", label: "Admin" }],
} as const;

function Nav() {
  const { session, logout } = useAuth();
  if (!session) return null;
  return (
    <nav aria-label="Main" className="flex items-center gap-1">
      {NAV[session.role].map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            cn(
              "rounded-control px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-surface-muted hover:text-ink",
              isActive && "bg-brand-soft text-ink",
            )
          }
        >
          {item.label}
        </NavLink>
      ))}
      <span className="mx-2 hidden text-sm text-ink-muted sm:inline">{session.displayName}</span>
      <Button variant="ghost" size="sm" onClick={logout}>
        Sign out
      </Button>
    </nav>
  );
}

function Layout() {
  return (
    <AppShell nav={<Nav />}>
      <Outlet />
    </AppShell>
  );
}

function Home() {
  const { session } = useAuth();
  return <Navigate to={session ? HOME_BY_ROLE[session.role] : "/login"} replace />;
}

function AdminPage() {
  return (
    <Card>
      <CardTitle>Administration</CardTitle>
      <p className="mt-2 text-sm text-ink-muted">The audit log viewer is added in milestone 3.</p>
    </Card>
  );
}

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: "login", element: <LoginPage /> },
      {
        path: "book",
        element: (
          <RequireRole allow="patient">
            <BookingPage />
          </RequireRole>
        ),
      },
      {
        path: "appointments",
        element: (
          <RequireRole allow="patient">
            <MyAppointmentsPage />
          </RequireRole>
        ),
      },
      {
        path: "schedule",
        element: (
          <RequireRole allow="clinician">
            <SchedulePage />
          </RequireRole>
        ),
      },
      {
        path: "admin",
        element: (
          <RequireRole allow="admin">
            <AdminPage />
          </RequireRole>
        ),
      },
      { path: "*", element: <Home /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}

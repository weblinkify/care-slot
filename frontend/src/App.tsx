import { createBrowserRouter, Navigate, NavLink, Outlet, RouterProvider } from "react-router";

import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/Button";
import { HOME_BY_ROLE, useAuth } from "@/features/auth/session";
import { AuditLogPage } from "@/features/audit/AuditLogPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { RequireRole } from "@/features/auth/RequireRole";
import { BookingPage } from "@/features/booking/BookingPage";
import { MyAppointmentsPage } from "@/features/booking/MyAppointmentsPage";
import { ProfilePage } from "@/features/profile/ProfilePage";
import { SchedulePage } from "@/features/schedule/SchedulePage";
import { cn } from "@/lib/cn";

const NAV = {
  patient: [
    { to: "/book", label: "Book" },
    { to: "/appointments", label: "My appointments" },
    { to: "/profile", label: "My data" },
  ],
  clinician: [{ to: "/schedule", label: "My day" }],
  admin: [{ to: "/admin", label: "Audit log" }],
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
        path: "profile",
        element: (
          <RequireRole allow="patient">
            <ProfilePage />
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
            <AuditLogPage />
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

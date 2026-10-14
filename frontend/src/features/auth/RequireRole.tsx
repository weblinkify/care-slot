import type { ReactNode } from "react";
import { Navigate } from "react-router";

import type { Role } from "@/api/types";

import { HOME_BY_ROLE, useAuth } from "./session";

/** UI-level guard for navigation only. The API enforces the real authorisation. */
export function RequireRole({ allow, children }: { allow: Role; children: ReactNode }) {
  const { session } = useAuth();
  if (!session) return <Navigate to="/login" replace />;
  if (session.role !== allow) return <Navigate to={HOME_BY_ROLE[session.role]} replace />;
  return children;
}

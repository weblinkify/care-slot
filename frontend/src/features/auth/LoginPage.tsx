import { useMutation } from "@tanstack/react-query";
import { useState, type SubmitEvent } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { ApiError } from "@/api/client";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardTitle } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";

import { HOME_BY_ROLE, useAuth } from "./session";

const DEMO_ACCOUNTS = [
  { username: "aino", label: "Aino - patient" },
  { username: "eero", label: "Eero - patient" },
  { username: "dr.aava", label: "Dr. Aava - clinician" },
  { username: "admin", label: "Admin" },
];

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const mutation = useMutation({
    mutationFn: () => login(username, password),
    onSuccess: (session) => {
      void navigate(HOME_BY_ROLE[session.role], { replace: true });
    },
  });

  function onSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate();
  }

  const error =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? "Sign-in failed"
        : null;

  return (
    <div className="mx-auto max-w-sm space-y-4">
      {searchParams.get("erased") === "1" && (
        <Alert tone="success">
          Your personal data has been deleted and you have been signed out.
        </Alert>
      )}
      <Card>
        <CardTitle>Sign in</CardTitle>
        <p className="mt-1 text-sm text-ink-muted">
          Mock identity provider - synthetic demo users only.
        </p>

        <form onSubmit={onSubmit} className="mt-5 space-y-4" noValidate>
          <Field label="Username">
            {({ id, className, describedBy }) => (
              <input
                id={id}
                className={className}
                aria-describedby={describedBy}
                autoComplete="username"
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                }}
                required
              />
            )}
          </Field>
          <Field label="Password" hint="Demo password: demo-password">
            {({ id, className, describedBy }) => (
              <input
                id={id}
                type="password"
                className={className}
                aria-describedby={describedBy}
                autoComplete="current-password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                }}
                required
              />
            )}
          </Field>

          {error && <Alert tone="danger">{error}</Alert>}

          <Button type="submit" className="w-full" disabled={mutation.isPending}>
            {mutation.isPending ? "Signing in..." : "Sign in"}
          </Button>
        </form>
      </Card>

      <section aria-labelledby="demo-accounts" className="mt-6">
        <h2 id="demo-accounts" className="text-sm font-medium text-ink-muted">
          Demo accounts
        </h2>
        <ul className="mt-2 flex flex-wrap gap-2">
          {DEMO_ACCOUNTS.map((account) => (
            <li key={account.username}>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setUsername(account.username);
                  setPassword("demo-password");
                }}
              >
                {account.label}
              </Button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

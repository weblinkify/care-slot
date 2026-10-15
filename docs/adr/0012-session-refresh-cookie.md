# 0012. Keep sessions across reloads with an HttpOnly refresh cookie

- **Status:** Accepted (amends the session handling of [0006](0006-authentication-mock-idp-rs256.md))
- **Date:** 2026-10-14

## Context
ADR-0006 kept the access token in memory only, so every page reload signed the user out.
That protected health data on shared computers but made the app tiresome to use: a refresh,
a new tab or an accidental reload meant signing in again. The access token must still never
be readable by script, because an XSS payload could then steal it.

## Decision
- The access token stays **in memory only** and keeps its 15-minute lifetime.
- On sign-in the IdP also sets a **refresh token** in a cookie that is `HttpOnly`, `Secure`,
  `SameSite=Strict` and scoped to `Path=/api/v1/auth`, so script cannot read it and it is
  never sent with ordinary API calls.
- It is a **browser-session cookie** (no `Max-Age`), so closing the browser still signs out.
  The token inside expires after **8 hours** (one shift) and is not extended on use.
- The refresh token is a JWT addressed to the IdP (`aud` = issuer, `typ=refresh`). The API
  requires its own audience, so a refresh token can never be used as an access token.
- `POST /auth/refresh` returns a new access token. The web app calls it on load and once
  whenever a request fails with 401 (an expired access token), then retries that request.
  `POST /auth/logout` clears the cookie.
- CSRF: `SameSite=Strict` stops cross-site requests from carrying the cookie. The endpoints
  only return JSON, which CORS (an explicit origin allow-list) hides from other origins.
- In the browser-only demo, the mock API keeps the demo user in `sessionStorage`, because a
  mocked response cannot set an `HttpOnly` cookie. Synthetic users only.

## Alternatives considered
- **Access token in `localStorage` or `sessionStorage`:** a small change, but any XSS
  payload could read the token.
- **Server-side sessions only (no bearer tokens):** a bigger change. It would bring CSRF to
  every endpoint and does not fit an API that several clients call (ADR-0006).
- **Rotating refresh tokens with reuse detection:** needs server-side state. That is the real
  IdP's job, and the mock does not try to copy it.

## Consequences
- A reload, a new tab or an expired access token no longer signs the user out.
- The mock IdP's refresh token is stateless, so logout clears the cookie but cannot revoke a
  copy taken elsewhere. Such a copy stays valid for up to 8 hours. A real IdP keeps
  server-side sessions and can revoke them, for example on `PatientErased`.
- CORS now allows credentials, which is safe only with an explicit origin list. Never use `*`.
- The web app shows a short loading state on start-up while it checks for a session.

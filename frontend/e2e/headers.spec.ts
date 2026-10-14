import { expect, test } from "@playwright/test";

// Regression guard: nginx silently dropped every security header for months-to-be because a
// location-level add_header disables inheritance. Checked on every deployed surface (nginx
// container, Vercel). The bare `vite preview` server sends none, so it opts out.
test.skip(process.env.E2E_SKIP_HEADERS === "1", "vite preview does not send security headers");

for (const path of ["/login", "/book", "/favicon.svg"]) {
  test(`security headers on ${path}`, async ({ request }) => {
    const headers = (await request.get(path)).headers();
    expect(headers["content-security-policy"]).toContain("default-src 'self'");
    expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["referrer-policy"]).toBe("no-referrer");
  });
}

import { expect, test } from "@playwright/test";

import { signIn, signOut } from "./helpers";

test("a reload keeps the user signed in until they sign out", async ({ page }) => {
  const heading = page.getByRole("heading", { name: "Book an appointment" });
  await signIn(page, "aino");
  await expect(heading).toBeVisible();

  // The session lives in an HttpOnly cookie: script (and so any XSS payload) cannot read it.
  const cookies = await page.context().cookies();
  expect(cookies.find((c) => c.name === "careslot_refresh")).toMatchObject({
    httpOnly: true,
    secure: true,
    sameSite: "Strict",
    path: "/api/v1/auth",
  });

  await page.reload();
  await expect(heading).toBeVisible();
  await expect(page).toHaveURL(/\/book$/);

  const loggedOut = page.waitForResponse((r) => r.url().endsWith("/auth/logout"));
  await signOut(page);
  expect((await loggedOut).status()).toBe(204);

  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

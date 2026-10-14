import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

export async function signIn(page: Page, username: string) {
  // After sign-out the app is already on /login. Avoid a full reload there: in demo mode the
  // in-browser API (and its data) would reset, just as the demo banner says.
  if (!page.url().endsWith("/login")) await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill("demo-password");
  await page.getByRole("button", { name: "Sign in" }).click();
}

export async function signOut(page: Page) {
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.waitForURL(/\/login$/);
}

/** A weekday at least two days ahead: outside the 2-hour change cut-off. */
export function bookableDay(offsetDays = 2): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

export async function expectNoA11yViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();
  expect(results.violations).toEqual([]);
}

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function signIn(page: Page, username: string) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill("demo-password");
  await page.getByRole("button", { name: "Sign in" }).click();
}

/** A weekday at least two days ahead: outside the 2-hour change cut-off, so it can be cancelled. */
function bookableDay(): string {
  const d = new Date();
  d.setDate(d.getDate() + 2);
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

async function expectNoA11yViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();
  expect(results.violations).toEqual([]);
}

test("patient books, sees and cancels an appointment", async ({ page }) => {
  await signIn(page, "eero");
  await expect(page.getByRole("heading", { name: "Book an appointment" })).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByLabel("Date").fill(bookableDay());

  // Pick the first free time of that day (keyboard-accessible radio group).
  const freeTimes = page.getByRole("group", { name: "Free times" });
  // Users click the visible label; the native radio inside is visually hidden.
  const firstSlot = freeTimes.locator("label").first();
  const time = (await firstSlot.innerText()).trim();
  await firstSlot.click();
  await expect(firstSlot.getByRole("radio")).toBeChecked();
  await page.getByRole("button", { name: "Book appointment" }).click();

  const confirmation = page.getByRole("status").filter({ hasText: "Booked for" });
  await expect(confirmation).toBeVisible();
  // e.g. "Booked for Fri 16 Oct, 08:00." -> "Fri 16 Oct, 08:00"
  const when = (await confirmation.innerText()).match(/Booked for (.+?)\./)?.[1] ?? "";
  expect(when).toContain(time);
  await expect(freeTimes.getByText(time, { exact: true })).toHaveCount(0); // slot is gone

  await page.getByRole("link", { name: "My appointments" }).first().click();
  // Earlier runs may have left a *cancelled* appointment at the same time (cancelled slots
  // are bookable again), so target the active one explicitly.
  const atTime = page.getByRole("listitem").filter({ hasText: when });
  const card = atTime.filter({ hasText: "booked" });
  await expect(card).toHaveCount(1);
  await expectNoA11yViolations(page);

  await card.getByRole("button", { name: /^Cancel/ }).click();
  await expect(card).toHaveCount(0);
  await expect(atTime.filter({ hasText: "cancelled" }).first()).toBeVisible();
});

test("patients cannot open the clinician view", async ({ page }) => {
  await signIn(page, "aino");
  await page.goto("/schedule"); // full reload drops the in-memory session by design
  await expect(page).toHaveURL(/\/login$/);
});

import { expect, test } from "@playwright/test";

import { bookableDay, expectNoA11yViolations, signIn, signOut } from "./helpers";

test("clinician opens a record with a stated reason; admin sees it in a verified audit log", async ({
  page,
}) => {
  // 1. A patient books with Dr. Aava (default clinician) -> creates a care relationship.
  const day = bookableDay(3);
  await signIn(page, "eero");
  await page.getByLabel("Date").fill(day);
  const slot = page.getByRole("group", { name: "Free times" }).locator("label").last();
  const time = (await slot.innerText()).trim();
  await slot.click();
  await page.getByRole("button", { name: "Book appointment" }).click();
  const confirmation = page.getByRole("status").filter({ hasText: "Booked for" });
  await expect(confirmation).toBeVisible();
  const when = (await confirmation.innerText()).match(/Booked for (.+?)\./)?.[1] ?? "";
  await signOut(page);

  // 2. The clinician opens that patient's record, stating why.
  await signIn(page, "dr.aava");
  await page.getByLabel("Day").fill(day);
  const entry = page.getByRole("listitem").filter({ hasText: time });
  await entry.getByLabel("Reason for access").selectOption("treatment");
  await entry.getByRole("button", { name: "Open record" }).click();
  await expect(entry.getByText("Eero Sample")).toBeVisible();
  await expect(entry.getByText("020794-****")).toBeVisible();
  await expectNoA11yViolations(page);
  await signOut(page);

  // 3. The admin sees the access with its reason, and the chain verifies.
  await signIn(page, "admin");
  await expect(page.getByRole("heading", { name: "Audit log" })).toBeVisible();
  const row = page
    .getByRole("row")
    .filter({ hasText: "patient.read" })
    .filter({ hasText: "treatment" });
  await expect(row.first()).toBeVisible();
  await page.getByRole("button", { name: "Verify integrity" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Chain intact" })).toBeVisible();
  await expectNoA11yViolations(page);
  await signOut(page);

  // 4. Clean up: free the slot again so repeated runs never exhaust the day.
  await signIn(page, "eero");
  await page.getByRole("link", { name: "My appointments" }).click();
  const booked = page.getByRole("listitem").filter({ hasText: when }).filter({ hasText: "booked" });
  await booked
    .first()
    .getByRole("button", { name: /^Cancel/ })
    .click();
  await expect(booked).toHaveCount(0);
});

import { expect, test } from "@playwright/test";

import { expectNoA11yViolations, signIn } from "./helpers";

test("patient grants and withdraws consent with a keyboard; history is kept", async ({ page }) => {
  await signIn(page, "aino");
  await page.getByRole("link", { name: "My data" }).click();
  await expect(page.getByText("150385-9013")).toBeVisible(); // own full identity code

  const research = page.getByRole("switch", { name: "Research use" });
  // Independent of starting state (the database is shared across runs): flip twice.
  const initial = (await research.getAttribute("aria-checked")) === "true";
  const flipped = String(!initial);

  // Keyboard only: focus the switch and press Space (WCAG 2.1.1).
  await research.focus();
  await page.keyboard.press("Space");
  await expect(research).toHaveAttribute("aria-checked", flipped);

  await research.press("Space"); // back to where it was, so reruns start the same
  await expect(research).toHaveAttribute("aria-checked", String(initial));

  await page.getByText(/Consent history/).click();
  await expect(page.getByText(/granted Research use/).first()).toBeVisible();
  await expect(page.getByText(/withdrawn Research use/).first()).toBeVisible();
  await expectNoA11yViolations(page);
});

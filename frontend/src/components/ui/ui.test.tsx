import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Alert } from "./Alert";
import { Button } from "./Button";
import { Field } from "./Field";

describe("ui primitives", () => {
  it("buttons default to type=button so they never submit forms by accident", () => {
    render(<Button>Save</Button>);
    expect(screen.getByRole("button", { name: "Save" })).toHaveAttribute("type", "button");
  });

  it("caller classes override variant defaults (tailwind-merge)", () => {
    render(<Button className="px-8">Wide</Button>);
    const cls = screen.getByRole("button").className;
    expect(cls).toContain("px-8");
    expect(cls).not.toContain("px-4");
  });

  it("field links label, hint and error to the control", () => {
    render(
      <Field label="Reason" hint="Optional" error="Too long">
        {({ id, className, describedBy, invalid }) => (
          <input
            id={id}
            className={className}
            aria-describedby={describedBy}
            aria-invalid={invalid}
          />
        )}
      </Field>,
    );
    const input = screen.getByLabelText("Reason");
    expect(input).toHaveAccessibleDescription("Optional Too long");
    expect(input).toBeInvalid();
  });

  it("danger alerts are announced assertively", () => {
    render(<Alert tone="danger">Failed</Alert>);
    expect(screen.getByRole("alert")).toHaveTextContent("Failed");
  });
});

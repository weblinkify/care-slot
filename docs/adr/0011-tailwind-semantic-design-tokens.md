# 0011. Tailwind CSS with semantic design tokens

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
The UI must be accessible (WCAG 2.2 AA), consistent, support light and dark mode, and be
easy for any developer, or AI agent, to extend without visual drift.

## Decision
- **Tailwind v4** via `@tailwindcss/vite`, configured in CSS (`src/index.css`).
- **Semantic tokens only:** components use `bg-surface`, `text-ink`, `border-line`,
  `bg-brand`, `text-danger-ink` and so on, defined once as CSS variables and exposed with
  `@theme inline`. Light/dark switching happens in one place, so components need no `dark:`
  colour variants. Raw palette colours and arbitrary values are not used in components.
- Every text/background pair is chosen for AA contrast. A missing `--danger-ink` token
  was caught in review because white on the dark-mode danger colour would have failed.
- **Primitives, not copy-paste:** `components/ui/*` with variants in `cva`; classes composed
  with `cn()` (`clsx` + `tailwind-merge`, so a caller's `px-6` reliably overrides a default
  `px-4`).
- **Accessibility through native elements and state variants:** real radios and checkboxes,
  `role="switch"` buttons. Styling uses `has-checked:`, `aria-checked:`,
  `has-focus-visible:` and `motion-reduce:`, so state and style cannot disagree.
- **Tooling:** `prettier-plugin-tailwindcss` sorts classes (including inside `cn`/`cva`).
  ESLint `jsx-a11y` runs in strict mode, and Playwright runs axe (WCAG 2.2 AA) on key screens.

## Alternatives considered
- **A component library (MUI, Chakra):** faster start, heavier bundle, and accessibility
  depends on how the library is used. Theming fights the library.
- **CSS Modules:** fine, but the design system then lives in conventions rather than tokens
  and utilities.

## Consequences
- Long class strings live in primitives, not pages.
- Changing the brand or contrast is a token change, not a hunt through components.
- Developers need to learn the token names. The VS Code workspace enables Tailwind
  IntelliSense with `cn`/`cva` support.

## 2024-05-15 - Accessible Composite UI Elements (Search Bars)
**Learning:** In composite elements like search bars consisting of a wrapper `div`, an icon, and an `input`, keyboard focus on the `input` isn't visually obvious on the parent container, and decorative icons might clutter screen readers.
**Action:** Use Tailwind's `focus-within:border-ink` (or similar) on the parent container to highlight it when the input is focused. Add `aria-hidden="true"` to decorative icons and `aria-label` to the input field itself to provide context to screen readers.

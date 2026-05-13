## 2024-05-13 - [Search Input Accessibility Enhancement]
**Learning:** Decorative icons placed next to input fields are read by screen readers if they lack the `aria-hidden` attribute. Additionally, input fields lacking labels require `aria-label` attributes to be accessible.
**Action:** Always add `aria-hidden="true"` to non-functional, decorative visual elements like search icons, and ensure all input fields have an accessible name using `aria-label` or `<label>` elements.

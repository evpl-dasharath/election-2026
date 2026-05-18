## 2024-05-18 - [Fix non-semantic clickable elements in GlobalHeader]
**Learning:** Interactive elements like logo links, statistic pills, and navigation menus were implemented using `div` and `span` tags with `onClick` handlers. This broke keyboard accessibility and screen reader support since these elements lacked implicit roles, focus states, and keyboard event handlers. Using semantic `<button>` tags natively solves these accessibility issues.
**Action:** Always use `<button>` or `<a>` for clickable elements. Avoid using `onClick` on non-interactive elements like `div` or `span`.

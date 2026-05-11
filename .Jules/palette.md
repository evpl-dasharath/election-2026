## 2024-05-11 - [Semantic HTML for Interactive Elements]
**Learning:** Found custom `div`/`span` elements acting as buttons with `onClick` handlers throughout the navigation components, breaking screen reader functionality and keyboard accessibility.
**Action:** Always replace interactive non-semantic elements with semantic `<button>` or `<a>` elements and apply `focus-visible:` utilities to ensure keyboard accessibility.

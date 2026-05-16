## 2024-05-16 - Replace structural tags with semantic buttons for navigation
**Learning:** The application uses many <div> and <span> elements with onClick handlers for key navigation elements (e.g. Logo, Header Links), which are inaccessible via keyboard and lack semantic meaning to screen readers.
**Action:** Replaced structural tags with semantic <button> tags for top-level navigation elements and added keyboard-accessible roles/handlers to interactive div elements acting as links. Also added focus-visible styles to make keyboard navigation explicit.

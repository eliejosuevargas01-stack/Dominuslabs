## 2024-08-24 - Accessibility improvements
**Learning:** Found multiple icon-only buttons in the application (like the hamburger menu in Sidebar.tsx, add task button in TaskChecklist.tsx, etc.) missing `aria-label` attributes. This is a common accessibility issue for screen readers.
**Action:** Adding `aria-label` to these interactive icon buttons to improve keyboard and screen reader accessibility.

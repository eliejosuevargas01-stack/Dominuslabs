## 2024-08-24 - Accessibility improvements
**Learning:** Found multiple icon-only buttons in the application (like the hamburger menu in Sidebar.tsx, add task button in TaskChecklist.tsx, etc.) missing `aria-label` attributes. This is a common accessibility issue for screen readers.
**Action:** Adding `aria-label` to these interactive icon buttons to improve keyboard and screen reader accessibility.

## 2026-08-25 - Login Form Accessibility
**Learning:** The login form lacked proper linkage between labels and inputs, and missing `autoComplete` properties. This affects screen readers' capability to read out the field name and hampers password managers from correctly filling out login forms.
**Action:** Always link `<label>` elements to `<input>` fields using `htmlFor` and `id`, and provide relevant `autoComplete` attributes (e.g., `username`, `current-password`) to enhance both accessibility and general UX.

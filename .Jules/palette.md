## 2024-08-24 - Accessibility improvements
**Learning:** Found multiple icon-only buttons in the application (like the hamburger menu in Sidebar.tsx, add task button in TaskChecklist.tsx, etc.) missing `aria-label` attributes. This is a common accessibility issue for screen readers.
**Action:** Adding `aria-label` to these interactive icon buttons to improve keyboard and screen reader accessibility.

## 2026-08-25 - Login Form Accessibility
**Learning:** The login form lacked proper linkage between labels and inputs, and missing `autoComplete` properties. This affects screen readers' capability to read out the field name and hampers password managers from correctly filling out login forms.
**Action:** Always link `<label>` elements to `<input>` fields using `htmlFor` and `id`, and provide relevant `autoComplete` attributes (e.g., `username`, `current-password`) to enhance both accessibility and general UX.

## 2024-08-26 - Password Visibility Toggle Accessibility
**Learning:** Interactive icon-only buttons used for toggling states (like the show/hide password eye icon) must not be removed from keyboard focus flow. The use of `tabIndex={-1}` prevented keyboard users from accessing this crucial functionality, violating basic accessibility (a11y) standards.
**Action:** Remove `tabIndex={-1}` from such interactive elements. Always provide descriptive, state-aware `aria-label` and `title` attributes (e.g., "Ocultar senha" vs "Mostrar senha") for screen readers and hover tooltips. Add clear `focus-visible` styling (like `focus-visible:ring-2`) to provide visual feedback for keyboard navigation.
## 2024-08-27 - Icon-only buttons accessibility in Omnichannel
**Learning:** Several icon-only utility buttons (like the search clear button and refresh conversations button) in complex views like OmnichannelView.tsx were missing `aria-label` attributes and keyboard focus states, making them invisible to screen readers and difficult to navigate via keyboard. There was also a Tailwind class typo (`-tranzinc-y-1/2`) which broke visual styling.
**Action:** Always add descriptive `aria-label` attributes and clear `focus-visible:ring-2 focus:outline-none` styles to all interactive icon-only elements. Validate Tailwind utility classes carefully.

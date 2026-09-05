## 2024-08-24 - Accessibility improvements
**Learning:** Found multiple icon-only buttons in the application (like the hamburger menu in Sidebar.tsx, add task button in TaskChecklist.tsx, etc.) missing `aria-label` attributes. This is a common accessibility issue for screen readers.
**Action:** Adding `aria-label` to these interactive icon buttons to improve keyboard and screen reader accessibility.

## 2024-08-25 - Login Form Accessibility
**Learning:** The login form lacked proper linkage between labels and inputs, and missing `autoComplete` properties. This affects screen readers' capability to read out the field name and hampers password managers from correctly filling out login forms.
**Action:** Always link `<label>` elements to `<input>` fields using `htmlFor` and `id`, and provide relevant `autoComplete` attributes (e.g., `username`, `current-password`) to enhance both accessibility and general UX.

## 2024-08-26 - Password Visibility Toggle Accessibility
**Learning:** Interactive icon-only buttons used for toggling states (like the show/hide password eye icon) must not be removed from keyboard focus flow. The use of `tabIndex={-1}` prevented keyboard users from accessing this crucial functionality, violating basic accessibility (a11y) standards.
**Action:** Remove `tabIndex={-1}` from such interactive elements. Always provide descriptive, state-aware `aria-label` and `title` attributes (e.g., "Ocultar senha" vs "Mostrar senha") for screen readers and hover tooltips. Add clear `focus-visible` styling (like `focus-visible:ring-2`) to provide visual feedback for keyboard navigation.

## 2024-08-27 - Accessibility on Input Clear Buttons
**Learning:** Icon-only interactive elements positioned inside inputs (like an 'X' to clear search terms) are easily missed during standard a11y checks because they visually appear as part of the input, but they require independent ARIA labels and focus states to be accessible to screen readers and keyboard users.
**Action:** Always verify that absolute-positioned action buttons inside inputs possess `aria-label`, `title`, and `focus-visible` outline styles, alongside standard hover states.

## 2024-09-05 - Pagination Controls Accessibility
**Learning:** Icon-only navigation buttons (like ChevronLeft/ChevronRight) for pagination and dynamic page number buttons often lack proper descriptive ARIA labels (`aria-label`, `title`) and active state indications (`aria-current`). This hides context from screen readers and makes keyboard navigation difficult if focus states are absent.
**Action:** Always provide descriptive `aria-label` attributes for pagination buttons, indicate the currently active page using `aria-current="page"`, and ensure visible focus states (`focus-visible:ring`) are applied to all interactive navigation elements.

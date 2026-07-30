# Component Guidelines

## Choose the Runtime Deliberately

- Use `.astro` for static markup, layouts, content rendering, and server/build
  data access. `src/pages/about.astro` is the standard content-page shape.
- Use `.svelte` only when UI needs persistent client interaction. Mount islands
  from Astro with the narrowest suitable client directive.
- Use an inline Astro `<script>` for small DOM behavior that does not justify a
  Svelte island. Because Swup replaces page fragments, initialization must be
  idempotent and normally re-run on `astro:page-load`.

References: `src/components/common/CoverImage.astro`,
`src/components/controls/LightDarkSwitch.svelte`,
`src/layouts/MainGridLayout.astro`.

## Props

- Define explicit props at the top of a component. Astro components use a local
  `Props` interface and `Astro.props`; Svelte 5 components use a typed `Props`
  destructure from `$props()`.
- Keep optional defaults at the boundary so templates do not repeatedly handle
  `undefined`.
- Import shared domain types from `src/types/`; keep one-off presentation props
  local to the component.
- Prefer callback props and explicit values over hidden module-global state.

## Composition and Styling

- Pages compose `MainGridLayout.astro`; the base shell stays in `Layout.astro`.
- Reuse shared components before duplicating cards, icons, pagination, Markdown,
  or image logic.
- Tailwind utility classes are the dominant styling mechanism. Component-scoped
  `<style>` is used for selectors, animation, or states that are awkward in
  utilities. Global tokens and reusable classes live under `src/styles/`.
- Use `class:list` in Astro and Svelte class directives for conditional state.

## Client Lifecycle

Swup makes a one-time `DOMContentLoaded` assumption unsafe. Browser behavior
must tolerate repeated page transitions:

- guard repeated custom-element registration or DOM initialization;
- subscribe during mount/init;
- remove listeners in Svelte `onMount` cleanup where ownership is local;
- use the established `astro:page-load`, `swup:enable`, or Swup hook patterns
  when behavior must be restored after navigation.

## Accessibility

- Interactive icons require an accessible name.
- Buttons, menus, and dialogs must use semantic elements and applicable ARIA
  roles/relationships.
- Images require useful `alt` text, or an empty `alt` only when decorative.
- Preserve keyboard operation and visible focus behavior when changing controls.

References: `src/components/controls/LightDarkSwitch.svelte` and
`src/components/common/CoverImage.astro`.

## Avoid

- Do not add client JavaScript to a static content-only page.
- Do not create React-style hooks; Firefly has no hook layer.
- Do not register the same listener on every Swup navigation without cleanup or
  an idempotency guard.
- Do not bypass existing image components for local optimized assets without a
  specific reason.

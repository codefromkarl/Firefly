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

## Scenario: Replace the Global Left Sidebar for One Page Family

### 1. Scope / Trigger

Use this contract when a route family needs a contextual directory or tool
panel in place of the configured Profile/Categories/Tags sidebar.

### 2. Signatures

- Page composition:
  `<ContextSidebar slot="left-sidebar" ... />`.
- Layout slot: `MainGridLayout` named slot `left-sidebar`.
- Dynamic container: `#left-sidebar-dynamic` in the Astro Swup container list.
- Presence marker: `[data-page-left-sidebar]`.

### 3. Contracts

- The configured global sidebar remains static and is not duplicated inside
  page content.
- Contextual sidebar markup lives inside `#left-sidebar-dynamic` so Swup
  replaces it on forward, back, and cached navigation.
- `Layout.astro` hides `#left-sidebar-wrapper` exactly when the dynamic
  container has a presence marker, and restores it otherwise.
- The custom sidebar uses the grid classes calculated by
  `MainGridLayout`; at 768px and below it follows the existing single-column
  sidebar policy.
- Static links remain useful without client JavaScript. JavaScript only
  reconciles the static-versus-dynamic sidebar after navigation.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Direct contextual-page load | Custom sidebar visible; global sidebar hidden |
| Default page → contextual page | Swup replaces dynamic sidebar and hides global sidebar |
| Contextual page → default page | Dynamic sidebar disappears and global sidebar returns |
| Browser back/forward | Same result as direct navigation, with no stale directory |
| Dynamic markup lacks the presence marker | Validation failure; both sidebar states can be wrong |

### 5. Good / Base / Bad Cases

- Good: route composes a static Astro directory through the named slot and
  tests a complete Swup round trip.
- Base: a route without the slot continues using the configured global sidebar.
- Bad: render a contextual directory inside `#swup-container` while leaving the
  global sidebar visible, or mutate the global sidebar contents in place.

### 6. Tests Required

Run `pnpm check`, `pnpm type-check`, and `pnpm build`. In a real browser,
exercise default → contextual index → contextual detail → back → default and
assert the marker, global wrapper visibility, directory contents, and browser
console at every step.

### 7. Wrong vs Correct

```astro
<!-- Wrong: duplicates a sidebar inside the main content column. -->
<MainGridLayout>
  <aside>Page directory</aside>
</MainGridLayout>
```

```astro
<!-- Correct: Swup owns the page-specific sidebar lifecycle. -->
<MainGridLayout>
  <BookSidebar slot="left-sidebar" books={books} />
  <BookLibrary books={books} />
</MainGridLayout>
```

## Scenario: Present an Explorable Book Knowledge Map

### 1. Scope / Trigger

Use this contract when a book graph is large enough that readers need both an
orientation-first outline and full semantic relationship exploration.

### 2. Signatures

- Island: `<BookKnowledgeGraph graph={graph} client:visible />`.
- Default view: `overview`.
- Views: `overview | relations | list`.
- Whole-book spine:
  `<BookMapSpine bookMap={graph.bookMap} nodes={graph.nodes} />`.
- Shared evidence renderer:
  `<BookGraphEvidence provenance={...} sourceRefs={...} />`.

### 3. Contracts

- Overview is summary-first: show core nodes, group remaining nodes by content
  section, and initially reveal only high-importance nodes when `bookMap` is
  absent.
- When `bookMap` exists, label the default tab “全书主线” and render the core
  question, thesis, ordered parts, entering/leaving understanding, transition
  rationale, related concepts, and conclusion. The semantic network remains a
  separate relationship-exploration tab.
- Reuse `BookGraphEvidence` for book-level statements, parts, transitions,
  graph nodes, and edges. Do not create a second provenance vocabulary in the
  spine component.
- Cytoscape is dynamically imported only after the reader opens relationship
  exploration; returning to another view does not destroy and recreate it.
- The list view renders every node and relationship as HTML and exposes the
  same provenance/evidence language as the overview and selected-node panel.
- Optional source quotes remain collapsed. A graph canvas is never the only
  path to content.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Initial visible hydration | Overview rendered; Cytoscape chunk not loaded |
| Graph has `bookMap` | Whole-book spine is the active default; every part and transition is readable |
| Graph lacks `bookMap` | Existing grouped concept overview remains the active default |
| Open relationship exploration | Canvas loads, sizes, and fits visible elements |
| Cytoscape import fails | Non-blocking error; HTML overview/list remain usable |
| Switch relation → list → relation | Existing canvas returns at non-zero size |
| No JavaScript | Server-rendered overview and native structure-list details remain readable |

### 5. Good / Base / Bad Cases

- Good: an argumentative book opens with its ordered spine and expands related
  concepts on demand; the relation tab remains available for non-linear
  exploration.
- Base: a 9-node graph uses the same views without forcing every group open.
- Bad: render all labels in a force graph as the default reading experience, or
  hide provenance in a canvas-only tooltip. Do not present unordered concept
  clusters as an author-ordered book spine.

### 6. Tests Required

Run scoped Biome, `pnpm check`, `pnpm type-check`, and `pnpm build`. In a real
browser, assert deferred Cytoscape loading, all three view transitions, a
non-zero canvas after returning, visible provenance, mobile layout, and no
console errors. For `bookMap`, assert the active tab label, ordered part
sequence, transition explanations, existing-node concept expansion, and no
horizontal overflow at 390px. Treat screenshots as rendering readiness, not
human visual acceptance.

### 7. Wrong vs Correct

```svelte
<!-- Wrong: the full network is the only/default content view. -->
<GraphCanvas {graph} />

<!-- Correct: one validated graph drives progressive, relational, and text views. -->
<BookGraphOverview {graph} />
<GraphCanvas {graph} hidden={activeView !== "relations"} />
<GraphStructureList {graph} />
```

```svelte
<!-- Correct inside BookGraphOverview: author order wins when it exists. -->
{#if graph.bookMap}
  <BookMapSpine bookMap={graph.bookMap} nodes={graph.nodes} />
{:else}
  <GroupedConceptOverview {graph} />
{/if}
```

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

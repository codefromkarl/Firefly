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

### Convention: Load Pagefind on Search Intent

Global navigation may render a search island on every route, but it must not
download Pagefind during an ordinary page view. Use the shared
`loadPagefind(): Promise<PagefindApi>` loader from
`src/utils/pagefind-loader.ts`; it deduplicates concurrent calls and stores the
initialized API on `window.pagefind`.

- The navbar search starts loading on focus, mobile panel open, or the first
  non-empty query.
- The dedicated `/search/` island starts loading in `onMount` because search is
  the page's primary purpose.
- Browser globals and DOM access stay behind `onMount` or an interaction
  callback so static rendering cannot execute them.
- A load failure leaves search empty and retryable; do not install a fake
  production API on `window`.

```typescript
// Wrong: every page downloads the search engine during initial HTML parsing.
loadPagefind();

// Correct: an interaction owns the optional dependency.
const handleSearchFocus = () => {
	void loadPagefind();
};
```

## Scenario: Keep Swup Navigation Visually Continuous

### 1. Scope / Trigger

Use this contract for every client-side Swup navigation, including ordinary
links, contextual directories, browser history, and cached visits.

### 2. Signatures

- Global owner: `src/layouts/Layout.astro`.
- Transition gate: `visit.animation.animate = false` in `visit:start`.
- Incoming-document cleanup:
  `hooks.before("content:replace", (visit) => { ... })`.
- Initial-load marker: `.onload-animation`.

### 3. Contracts

- `.onload-animation` belongs only to a real document load. Before every Swup
  content replacement, remove it from the detached `visit.to.document`.
- Every Swup visit uses an opaque atomic replacement. Keep the current document
  visible while fetching, skip the multi-container exit/enter animation, then
  replace all configured containers in one render step.
- Swup still owns fetch, cache, history, head updates, container replacement,
  progress feedback, lifecycle hooks, and normal scroll behavior. Disabling
  animation must not fall back to `window.location` navigation.
- Route-specific code may override scroll behavior, but it must not reintroduce
  a second page-transition animation owner.
- Direct loads may retain `.onload-animation`; client navigations must not
  replay it.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Direct URL load | Initial-load animation may run and content becomes fully visible |
| Ordinary internal link | `animation:skip` fires; every Swup container and incoming `#content-wrapper` stays at opacity `1` |
| Cached second navigation | Same opaque replacement; no stale `.onload-animation` |
| Browser back/forward | Same opaque replacement and no document reload |
| Route-specific preserved scroll | Opaque replacement plus the route's explicit scroll contract |
| Swup cannot replace required containers | Existing Swup mismatch/error path; do not hide it with a hard reload |

### 5. Good / Base / Bad Cases

- Good: the old page remains readable during fetch and the complete incoming
  page replaces it without a blank frame.
- Base: a direct load performs the short initial entrance once.
- Bad: fade all Swup containers to zero, or disable the outer Swup animation
  while allowing a nested `.onload-animation` to blank the incoming content.

### 6. Tests Required

Run scoped Biome, `pnpm check`, `pnpm type-check`, and `pnpm build`. In a
production preview, test an ordinary link, a cached second link, a contextual
link, and browser back/forward at desktop and 390px. Across each transition,
sample animation frames and assert:

- the JavaScript document identity and Navigation Timing entry count remain
  unchanged;
- `animation:skip` fires and `animation:out:start` does not;
- `#swup-container`, `#content-wrapper`, all configured sidebars, and banner
  containers have minimum opacity `1`;
- the incoming `#content-wrapper` no longer has `.onload-animation`;
- URL, title, current-link state, normal/preserved scroll behavior, and root
  overflow remain correct.

### 7. Wrong vs Correct

```typescript
// Wrong: independent outer and inner animations can both create blank frames.
swup.hooks.on("link:click", (visit) => {
  visit.animation.animate = true;
});

// Correct: one global owner keeps Swup navigation opaque.
swup.hooks.on("visit:start", (visit) => {
  visit.animation.animate = false;
});

swup.hooks.before("content:replace", (visit) => {
  visit.to.document
    ?.querySelectorAll(".onload-animation")
    .forEach((element) => element.classList.remove("onload-animation"));
});
```

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
- Book-to-book navigation marker: `[data-book-directory-navigation]`.

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
- Clicking a marked book-directory link preserves the current window scroll
  position. The `link:click` hook sets `visit.scroll.reset = false` and
  `visit.meta.preserveWindowScroll = true`; the global `visit:start` hook must
  skip its eager `window.scrollTo` for that visit.
- Book links use the same opaque Swup lifecycle as every other internal link.
  The marker owns only the book-specific scroll exception; it must not create
  a second animation policy.
- This exception is narrow. Library cards, global navigation, unmarked detail
  links, and direct loads keep the normal reset-to-top behavior.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Direct contextual-page load | Custom sidebar visible; global sidebar hidden |
| Default page → contextual page | Swup replaces dynamic sidebar and hides global sidebar |
| Contextual page → default page | Dynamic sidebar disappears and global sidebar returns |
| Browser back/forward | Same result as direct navigation, with no stale directory |
| Marked book → book navigation at scroll Y | Destination keeps the same Y when its height permits and uses the global opaque Swup lifecycle |
| Unmarked library card → book navigation | Global opaque Swup lifecycle plus reset-to-top behavior |
| Dynamic markup lacks the presence marker | Validation failure; both sidebar states can be wrong |

### 5. Good / Base / Bad Cases

- Good: route composes a static Astro directory through the named slot and
  tests a complete Swup round trip; book-directory navigation preserves the
  reader's vertical context without blanking all Swup containers.
- Base: a route without the slot continues using the configured global sidebar.
- Bad: render a contextual directory inside `#swup-container` while leaving the
  global sidebar visible, mutate the global sidebar contents in place, or set
  `visit.scroll.reset = false` without also bypassing the layout's eager
  `visit:start` scroll.

### 6. Tests Required

Run `pnpm check`, `pnpm type-check`, and `pnpm build`. In a real browser,
exercise default → contextual index → contextual detail → back → default and
assert the marker, global wrapper visibility, directory contents, and browser
console at every step. From a scrolled detail page, use the book directory for
two consecutive book switches at desktop and 390px widths; assert
`after.scrollY === before.scrollY`, the new link has `aria-current="page"`, and
the root has no horizontal overflow. Apply the global opaque-navigation checks
from the preceding scenario. Then open a detail from an unmarked library card
and assert it uses the same opaque lifecycle while following the normal
reset-to-top path.

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

```typescript
// Wrong: Swup core no longer resets, but Layout.astro already jumped to top.
visit.scroll.reset = false;

// Correct: the marker owns only the route-specific scroll exception.
visit.scroll.reset = false;
visit.meta.preserveWindowScroll = true;
```

## Scenario: Present a Three-Section Book Detail

### 1. Scope / Trigger

Use this contract for the public book card, book directory, and detail page.

### 2. Signatures

- Detail route: `src/pages/books/[...slug].astro`.
- Detail sidebar: `<BookSidebar books={books} />`.
- Card: `<BookCard book={book} />`.
- Ordered section IDs:
  `book-introduction`, `why-read`, `classic-excerpts`.
- Public content fields:
  `introductions`, `readingReasons`, `endorsements`, `excerpts`.

### 3. Contracts

- The detail page renders exactly three first-level content sections and keeps
  their order stable: whole-book introduction, places worth reading, classic
  excerpts. The visible second label is “这本书值得看的地方”; avoid the
  universal claim implied by “为什么需要看这本书”.
- The sidebar page directory contains exactly those same three labels and
  anchors. Do not derive it from unpublished Markdown headings.
- Book cards use `introductions[0].text` as their preview and identify their
  link as opening a book introduction. They do not consume unsourced
  `whyRead`, or show `graphStage` or a knowledge-map badge.
- The introduction section renders sourced official/publisher descriptions as
  continuous prose under the visible “书籍简介” heading. Curated books render
  three complementary paragraphs in source order; do not style these summaries
  as quotation cards or add quotation marks. Deduplicate identical source URLs
  and list the named external sources below the prose. The card preview still
  uses only the first introduction.
- The detail cover is evidence, not a decorative crop. Its container provides
  a mobile book-like aspect ratio and a desktop minimum height; the image uses
  `object-contain` with breathing room so the complete front cover remains
  visible across source ratios. Do not use `object-cover` on the detail cover.
- The why-read section renders two to four source-backed
  `readingReasons`. Each card has an editorial navigation title, a distinct
  reader-value `kind`, sourced text, visible attribution, and a
  “查看依据来源” link. The supported kinds are `insight`, `scope`,
  `perspective`, `readability`, `application`, and `boundary`.
- Generic prestige praise such as “best writer” or “must-read classic” does
  not qualify as a reading reason because it does not tell the reader what the
  whole book provides. Preserve useful praise only in the optional
  `endorsements` area below the reason cards; it remains inside the same
  first-level section.
- Translation markers belong in the visible attribution. Opening an external
  source uses a normal anchor with `target="_blank"` and `rel="noreferrer"`;
  the static page remains useful without JavaScript.
- Let the source, quotation, attribution, and link carry the editorial
  explanation. Do not add defensive copy about AI, the site's neutrality, or
  how the reader should judge the book. Do not place generic uppercase English
  eyebrows above the three Chinese section headings.
- Render excerpts as semantic blockquotes with visible sources. Preserve source
  order and do not turn the excerpt list into a carousel or hidden interaction.
- If an excerpt has a public verification `url`, render a normal
  “核对公开原文” anchor beside its source. Local-edition excerpts need no
  artificial URL; their chapter/section locator remains visible.
- When `excerpts` is empty, render a visible pending state that explains the
  site will not use AI to invent quotations.
- The public detail is static Astro output. Do not import `BookKnowledgeGraph`,
  call `getGraphForBook`, add a graph client directive, or otherwise load
  Cytoscape from the book route.
- Historical graph components may remain in the repository for internal
  reference, but they have no public-route ownership.
- At desktop and mobile widths, the three sections remain readable in normal
  document flow and page-root horizontal overflow is forbidden.
- Swup directory switching preserves its established scroll behavior; normal
  card navigation continues to reset to the top.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Detail route renders | Exactly three required sections and sidebar links exist |
| Book has sourced introduction/reasons | Visible attribution and original-source links exist |
| Cover aspect ratio differs from the container | Complete cover remains visible with optional empty background space |
| Several introduction paragraphs use one URL | Prose renders in order and the source link appears once |
| Reading reasons repeat a `kind` | Content sync/build fails |
| Book has a generic prestige quote only | Editorial review fails; move it to `endorsements` and add concrete reasons |
| Source is a translation | Translation marker is visible in the attribution |
| Book has excerpts | Ordered blockquotes and their sources are visible |
| Excerpt has a public verification URL | Visible “核对公开原文” link opens that URL |
| Book has no excerpts | Honest pending/no-fabrication state is visible |
| Detail has no JavaScript | All three sections remain readable |
| Inspect loaded resources | No graph island or Cytoscape resource is present |
| Viewport is 390px | Sections form one readable column and root `scrollWidth <= clientWidth` |
| Switch book through directory | New title/anchors update and established scroll behavior is preserved |
| Open detail from library card | Normal navigation resets to the top |

### 5. Good / Base / Bad Cases

- Good: the card previews the first sourced introduction; the detail explains
  at least two distinct reader benefits with publisher/review evidence, keeps
  prestige praise secondary, and ends with verified excerpts. The detail cover
  is fully visible, while the introduction reads as prose with compact sources.
- Base: a book without checked source text shows the explicit pending state.
- Bad: crop a book cover with `object-cover`, render three summary paragraphs
  as three oversized quotation cards, use “one of the greatest writers” as the
  sole answer to why a book is worth reading, show an unlinked AI-written
  recommendation, hide translation status, add process disclaimers to the
  reading flow, mount a graph island, expose a graph-stage badge, render
  Markdown notes as a fourth section, or invent an author quote.

### 6. Tests Required

Run scoped Biome, `pnpm check`, `pnpm type-check`, and `pnpm build`. Audit all
generated book details for the exact three section IDs and absence of graph
labels/runtime references, generic English eyebrows, and defensive AI/process
copy. Assert every detail renders two to four reason cards with unique kinds,
source links, and titles; endorsements, when present, remain visually
secondary. Curated details also render three introduction paragraphs, one link
per unique introduction URL, and at least three unique excerpt cards, while 17
library cards continue to use only the first introduction preview. In a real
browser, cover the narrowest and widest cover ratios at desktop and 390px,
plus a page with three reasons and an endorsement, a local-edition excerpt
page, a page with public excerpt links, the library filters, and Swup
navigation. Assert the full cover edges are visible, sources are named, no
Cytoscape request occurs, and there is no root overflow or console error.
Treat screenshots as rendering readiness, not human visual acceptance.

### 7. Wrong vs Correct

```astro
<!-- Wrong: unused graph data still creates a public runtime island. -->
<BookKnowledgeGraph graph={graph} client:visible />
<p>{book.data.whyRead}</p>
<Image src={book.data.cover} class="h-full w-full object-cover" />

<!-- Correct: structured book fields produce the complete public document. -->
<section id="book-introduction">
  <Image src={book.data.cover} class="h-full w-full object-contain" />
  <h2>书籍简介</h2>
  {book.data.introductions.map(renderIntroductionParagraph)}
  {uniqueIntroductionSources.map(renderIntroductionSource)}
</section>
<section id="why-read">
  {book.data.readingReasons.map(renderReadingReason)}
  {book.data.endorsements.map(renderSecondaryEndorsement)}
</section>
<section id="classic-excerpts">{/* excerpts or honest pending state */}</section>
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

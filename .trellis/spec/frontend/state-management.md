# State Management

Firefly has no global state library. Most site data is static at build time,
while interactive state is local to Svelte islands or browser settings.

## State Categories

- Build-time content: load through Astro content collections and utility
  functions, as in `src/utils/content-utils.ts`.
- Component state: use Svelte 5 `$state` and `$derived`, with typed `$props()`.
  `src/components/pages/anime/AnimeGrid.svelte` demonstrates filters, sorting,
  pagination, and modal selection.
- Persisted display preferences: keep storage and DOM application in shared
  helpers such as `src/utils/setting-utils.ts`; components render and invoke
  those helpers.
- Dynamic remote data: keep loading, failure, and result states together in the
  owning island, as in `src/components/pages/dynamic/DynamicFeed.svelte`.
- URL state: use normal URLs and query parameters for navigable search,
  categories, and tags rather than an in-memory store.

## Derived and Shared State

- Use `$derived` for values computable from props or local state; do not maintain
  duplicate mutable copies.
- Keep state local until multiple independent islands genuinely require a
  shared browser contract.
- When cross-component behavior is already represented by DOM classes, custom
  events, or local storage, use the established helper/event pattern rather
  than introducing a store.

## Lifecycle

- Initialize browser-dependent state in `onMount`.
- Clean up window/document listeners owned by the component.
- Account for Swup content replacement when state must be re-read after
  navigation.
- Keep browser globals behind explicit checks or client-only lifecycle code so
  static builds remain valid.

## Avoid

- Do not introduce a global store for static content or one component's state.
- Do not mutate props to represent derived UI state.
- Do not read `window`, `document`, or local storage at module evaluation time.
- Do not cache remote data in two competing places without a defined owner.

## Scenario: Synchronize Book Filters Through the URL

### 1. Scope / Trigger

Use this contract when changing the `/books/` keyword, shelf, reading-status,
or topic filters, or when projecting the selected shelf into the contextual
book directory.

### 2. Signatures

- Query parameters: `q`, `shelf`, `status`, and `topic`.
- Closed values: `BOOK_SHELF_VALUES` and `BOOK_STATUS_VALUES`.
- Directory projection hook: `data-book-shelf-group`.

### 3. Contracts

- `window.location.search` is the single navigable source of filter state.
  Missing parameters mean “all”; invalid closed values normalize to “all”.
- `BookLibrary.svelte` reads URL state in `onMount` and on `popstate`, and
  writes normalized state with `history.replaceState`.
- `BookLibrary.svelte` is the only filter interaction owner. Keyword, shelf,
  status, topic, current-condition chips, result count, and clear action stay
  in the main content area.
- The contextual sidebar is stable navigation. Keyword, status, and topic
  filters must never hide or remove directory books.
- A selected shelf may only open and lightly style its matching native
  `details[data-book-shelf-group]`; this directory projection is not a second
  filter control or state store.
- Detail pages do not render a duplicate filter card. They open the current
  book's shelf server-side and mark the current book with `aria-current`.
- The island owns and removes its single `popstate` listener.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Missing query parameter | Corresponding control uses “all” |
| Unknown shelf/status/topic | Normalize to “all”; do not create an invalid selection |
| Refresh a filtered URL | Controls, cards, and counts restore; matching shelf group opens |
| Keyword/status/topic filter | Directory retains every book and its existing open state |
| Detail navigation then browser back | Previous query and filtered result return |
| Swup replaces the library | Old listeners are removed; new island owns one set |
| JavaScript unavailable | Directory links still navigate to the list or detail pages |

### 5. Good / Base / Bad Cases

- Good: choose a shelf in the main controls, refine by topic, refresh, enter a
  book, and return to the same filtered result while the directory remains
  complete.
- Base: `/books/` has no parameters and displays every book.
- Bad: hide directory books to mirror the result set or maintain a second
  filter island in the sidebar.

### 6. Tests Required

Run `pnpm check`, `pnpm type-check`, and `pnpm build`. In a browser, assert a
combined URL filter, selected shelf projection, all directory books remaining
available, clear, refresh restoration, detail → back restoration, and a 390px
viewport without horizontal overflow or hidden main controls.

### 7. Wrong vs Correct

```typescript
// Wrong: temporary results erase stable navigation.
directoryBooks = books.filter((book) => book.status === activeStatus);

// Correct: validate URL state; only project the shelf as a directory hint.
const params = new URL(window.location.href).searchParams;
const shelf = params.get("shelf");
activeShelf = isBookShelf(shelf) ? shelf : "all";
selectedShelfDetails.open = activeShelf === selectedShelfDetails.dataset.bookShelfGroup;
```

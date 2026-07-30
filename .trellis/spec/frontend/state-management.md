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

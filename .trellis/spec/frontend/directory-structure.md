# Directory Structure

## Runtime Layout

```text
src/
├── assets/          # source-managed images processed by Astro
├── components/      # Astro and Svelte UI grouped by responsibility
├── config/          # typed site and feature configuration
├── constants/       # shared and generated constants
├── content/         # posts, dynamic entries, and special-page Markdown
├── i18n/            # keys, language maps, and lookup helpers
├── layouts/         # base document and page grid
├── pages/           # Astro file-based routes and endpoints
├── plugins/         # remark/rehype transformations
├── styles/          # global and feature styles
├── types/           # shared and config contract types
├── utils/           # content, URL, image, date, and setting helpers
└── workers/         # browser Web Worker implementations
```

Files in `public/` are copied as-is. Use `src/assets/` when Astro should import,
optimize, or fingerprint an image. `src/content.config.ts` owns content schemas.

## Ownership

- Page files under `src/pages/` should assemble layouts and domain components;
  keep reusable UI in `src/components/`.
- Components are grouped by role: `common/`, `controls/`, `features/`,
  `layout/`, `misc/`, page-specific `pages/`, and sidebar `widget/`.
- Site switches and user-editable values belong in `src/config/`, with shared
  shapes in `src/types/`. Export broadly used config through
  `src/config/index.ts`.
- Cross-component pure behavior belongs in `src/utils/`. Markdown AST behavior
  belongs in `src/plugins/`.
- Build-time operations stay in `scripts/`; do not move them into browser code.

Evidence: `src/pages/about.astro`, `src/layouts/MainGridLayout.astro`,
`src/config/index.ts`, and `src/utils/content-utils.ts`.

## Naming

- Astro and Svelte components use `PascalCase`: `CoverImage.astro`,
  `AnimeGrid.svelte`.
- Configuration modules use `camelCase` and normally end in `Config.ts`;
  existing exceptions such as `backgroundWallpaper.ts` are retained.
- Utilities use descriptive kebab-case names such as `url-utils.ts`.
- Page paths follow Astro file routing, including `[...slug].astro`.
- Content directories define stable post IDs and URLs. Prefer
  `src/content/posts/<slug>/index.md` when a post owns adjacent images.

Use the aliases from `tsconfig.json` (`@/`, `@components/`, `@utils/`,
`@i18n/`, and others) instead of deep relative imports when crossing folders.

## Avoid

- Do not put directly served files in `src/public`; the real static root is
  `public/`.
- Do not create a parallel config or type barrel outside `src/config/index.ts`
  and `src/types/config.ts`.
- Do not place shared logic in a page frontmatter block when it already belongs
  in `src/utils/` or a component.

# Type Safety

The project uses TypeScript with Astro's base config, bundler resolution, and
`strictNullChecks`. `pnpm type-check` also checks isolated declarations.

## Type Placement

- Put shared domain and configuration types in `src/types/`.
- Keep each configuration object paired with its type module, for example
  `src/config/siteConfig.ts` and `src/types/siteConfig.ts`.
- Re-export shared types from `src/types/config.ts` and configuration values
  from `src/config/index.ts`.
- Keep component-only `Props` and small internal helper types local.
- Use Astro `CollectionEntry<"posts">` instead of rebuilding content types.

## Runtime Validation

`src/content.config.ts` is the runtime/build contract for Markdown data:

- define collection fields with `astro/zod`;
- use defaults for optional frontmatter consumed throughout templates;
- keep the declared `PostData`/`DynamicData` shapes aligned with schemas;
- run `pnpm check` and `pnpm build` after schema or content changes.

Configuration modules are compile-time typed, not runtime validated. Never place
untrusted runtime data into them.

## Patterns

- Use literal unions for closed config choices, as in `LIGHT_DARK_MODE` and
  `WALLPAPER_MODE`.
- Use `import type` in TypeScript files where Biome requests it; Astro/Svelte
  files have relaxed lint rules but should still be clear.
- Narrow browser DOM values to the actual element type near the query/event
  boundary.
- Model external API responses in `src/types/` before page components consume
  them.

## Avoid

- Do not add `any` to bypass collection, config, or external API contracts.
- Do not duplicate a config shape inline in multiple consumers.
- Do not use broad assertions to hide missing null checks.
- Do not add a frontmatter field only to Markdown; update
  `src/content.config.ts` and all consumers together.

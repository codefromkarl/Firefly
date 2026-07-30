# Firefly Frontend Guidelines

Firefly is a static-first Astro 7 site with Svelte 5 islands. TypeScript
configuration and Astro content collections are the main contracts; interactive
state stays inside Svelte components or small browser scripts.

## Pre-Development Checklist

Read the guides that match the change:

- Always read [Directory Structure](./directory-structure.md).
- For `.astro` or `.svelte` work, read
  [Component Guidelines](./component-guidelines.md).
- For content, site identity, feature flags, or assets, read
  [Content and Configuration](./content-and-configuration.md).
- For interactive behavior, read [State Management](./state-management.md).
- For new or changed data shapes, read [Type Safety](./type-safety.md).
- Before handoff, read [Quality Guidelines](./quality-guidelines.md).

There is no custom-hook layer in this repository. Do not introduce React-style
`use*` abstractions; follow Astro composition, Svelte runes, or shared utilities.

## Quality Check

Run the checks required by the touched scope:

```bash
pnpm check
pnpm type-check
pnpm build
```

Use `pnpm dev` or `pnpm preview` for visual and interactive changes. Run Biome
on changed source when code, rather than content only, was modified.

## Guides

| Guide | Covers |
| --- | --- |
| [Directory Structure](./directory-structure.md) | Ownership, routing, assets, naming |
| [Component Guidelines](./component-guidelines.md) | Astro/Svelte boundaries, props, styling, accessibility |
| [Content and Configuration](./content-and-configuration.md) | Content schemas, URLs, config/type pairs, assets |
| [State Management](./state-management.md) | Svelte runes, browser persistence, static/server data |
| [Type Safety](./type-safety.md) | Type placement, collection validation, assertions |
| [Quality Guidelines](./quality-guidelines.md) | Formatting, build pipeline, checks, generated files |

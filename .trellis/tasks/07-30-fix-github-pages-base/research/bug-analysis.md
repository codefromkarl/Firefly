# Bug Analysis: GitHub Pages workflow succeeded with broken subpath assets

## 1. Root Cause Category

- **Category**: D - Test Coverage Gap, with an E - Implicit Assumption
  contributor.
- **Specific Cause**: the site and content assumed root-path hosting while the
  repository Pages URL publishes below `/Firefly/`. CI checked that Astro could
  build and Pages could upload the artifact, but did not check the deployed
  URL or generated link paths.

## 2. Why Fixes Failed

1. **Initial deployment**: GitHub Actions reported success, but the generated
   asset URLs still began at `/_astro/`, so the browser requested the user-site
   root instead of the repository path.
2. **Configuration-only fix**: setting Astro's base corrected most components
   through the existing `url()` helper, but RSS URL construction, the profile
   RSS link, and Markdown-authored local links bypassed that helper.
3. **Complete fix**: parameterize both `site` and `base`, route component/feed
   paths through `url()`, use relative Markdown links, and audit the generated
   HTML rather than only the source.

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | Use `ASTRO_SITE_URL` and `ASTRO_BASE_PATH` together | Done |
| P0 | Code reuse | Route local component/feed URLs through `url()` | Done |
| P0 | Integration check | Build both root and Pages variants | Done |
| P0 | Artifact check | Reject root-absolute HTML paths and missing assets | Done |
| P0 | Production check | Request representative live URLs after deployment | Done |
| P1 | Platform access | Authenticate Wrangler before a custom-domain cutover | Pending |

## 4. Systematic Expansion

- **Similar issues**: RSS/canonical URLs, favicons, Pagefind assets, Markdown
  links, and disabled-route behavior can all differ between root and subpath
  hosting.
- **Design improvement**: keep one `url()` helper as the internal-path boundary
  and pass deployment-specific origin/base through the build environment.
- **Process improvement**: treat workflow success and live deployment
  verification as separate gates.

## 5. Knowledge Capture

- [x] Added the subpath deployment contract to
      `.trellis/spec/frontend/content-and-configuration.md`.
- [x] Added the alternate-target production check to
      `.trellis/spec/frontend/quality-guidelines.md`.
- [x] Kept the project-local spec as the source of truth; this repository has no
      `src/templates/markdown/spec/` mirror to synchronize.

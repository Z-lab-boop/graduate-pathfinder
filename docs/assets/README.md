# Public site documentation captures

`site-home.png`, `site-explore.png` and `site-docs.png` are browser-generated product screenshots, separate from the labeled conceptual artwork under `web/site/assets/generated/`. Explore contains committed fictional data only. No real applicant, institution, material or admissions outcome is represented.

Regenerate from the repository root with `npm --prefix web run capture:site`. The command builds the site, forks exactly `web/site/capture-server.mjs` with private Node IPC, binds port 0 on 127.0.0.1, and validates the owned child PID, canonical root, host and dynamic port before Chromium launches. No fixed/foreign HTTP listener can signal readiness. Root/bind errors, timeout, early exit and invalid IPC reject capture. The owned child is always terminated, including browser/page failures.

All three captures use English (`en-US` browser locale; explicit English site state), UTC, 1440×1000 CSS pixels, device scale 1, light color scheme and reduced motion. The exact clip is `{ x: 0, y: 0, width: 1440, height: 1000 }`; this is the initial top viewport, not a full-page record. Home uses its initial Profile stage. Explore uses the initial Northlake target, Materials tab, all evidence filters enabled, and no open inspector/dialog. Docs shows the field-guide heading, navigation to installation/privacy and the capability overview. Lower page content is intentionally outside these documented viewport captures.

Capture waits for same-origin resources, the validated synthetic view, all local images and `document.fonts.ready`. It clears local language state, blurs focus, scrolls to the top, hides the caret and disables screenshot animations. External resource requests cause failure. All three images are staged beside their destinations; only after successful capture are they atomically renamed, so a page/render failure preserves approved images. Temporary files are ignored and cleaned up.

Run twice on the same platform/browser/font environment, then compare `shasum -a 256 docs/assets/site-*.png`. Byte equality is expected within that environment; cross-platform/font/browser equality is not promised. Inspect originals at their native dimensions for missing imagery, clipped copy, labels and private text. Agent visual inspection is not independent human approval.

Run `node scripts/check-site-assets.mjs` for PNG signatures, exact 1440×1000 dimensions, 20,000–900,000 byte limits (exclusive), both README references/alt text, exact Pages URLs, local images, pinned artwork provenance, and binary release allowlist exclusion. Tests exercise missing/oversized/wrong-size assets, empty alt text, stale links, remote hotlinks, changed provenance, release globs, foreign HTTP 200, invalid IPC and failure preservation.

The approved artwork PNGs remain unchanged. Local lossless WebP delivery reduces artwork transfer by 32.49% with exact decoded RGBA equality; the originals are retained for provenance and fallback. See the [artwork audit](../../web/site/assets/generated/README.md) for byte counts, commands, hashes and storage tradeoff.

These are repository documentation assets, **not release binaries**. No tagged binary release is published. Capturing, testing or documenting intended Pages URLs does not establish hosted CI success, deployment, live acceptance, real material authenticity or admissions-data completeness.

# Admissions Evidence Atlas concept artwork

These original, AI-generated images are visual metaphors, not authentic admissions documents, applicant evidence, product screenshots, or photographs of real institutions. The site labels each image “Concept artwork”; the separate HTML flow is labeled “Synthetic product walkthrough”.

Tool: built-in `image_gen.imagegen` (no CLI/API fallback). Generation date: **2026-10-10 Asia/Shanghai** (2026-10-09 UTC). All final PNGs are copied unchanged from the tool output, with original provenance metadata retained. The tool does not expose a stable model-version identifier.

| Final asset | Dimensions | SHA-256 |
| --- | --- | --- |
| `admissions-atlas-hero.png` | 1536 × 1024 (3:2) | `e626a33f3bc1f3ab7b48e57ace625aab27ffa3af781226a82ab863f49f2a658d` |
| `materials-review.png` | 1448 × 1086 (4:3) | `bd8c3fd171d3e72b8f330ebe872f5682bef52b78a2a8a1a9e20d779d95c1809b` |
| `campus-route.png` | 1672 × 941 (approximately 16:9) | `f8677b7dcf871792029a48305320a48e5b5546e09b1f0beb412503ddfd2fa831` |

## Prompts and inspection

### admissions-atlas-hero.png

Initial prompt:

> 3:2 editorial photograph, overhead archival admissions desk, anonymous layered application folders with no readable text, translucent timeline strips, brass measuring tools, cinnabar registration marks, distant abstract campus silhouette reflected in dark glass, warm bone paper against deep navy, museum catalog lighting, tactile grain, no people, no logo, no watermark, no institution identity.

The first result was **rejected**: visible ruler numerals/compass glyphs and overly specific Gothic campus imagery. It is not included in the project. A separate built-in generation call used the exact original brief plus this targeted correction:

> Correction to avoid unwanted identity/text: all brass tools are plain unengraved dividers or simple unnumbered tick-only scales; absolutely no alphabet, numbers, compass lettering, pseudo-writing, photographs or drawings printed on documents. All folder surfaces are entirely blank. The distant reflected silhouette consists only of indistinct low rectangular fictional buildings, no Gothic towers, landmarks, churches or identifiable campus architecture.

Final original-pixel inspection: blank folders, unnumbered ticks and plain dividers; indistinct rectangular background architecture. No apparent text, logos, people, watermark or recognizable institution. Accepted output identifier: `exec-d623e5d6-ec6e-481d-8fcc-52645f5208e7`.

### materials-review.png

> 4:3 macro editorial photograph of anonymous document layers, blank recommendation envelope, embossed seal impressions without letters, checklist geometry without readable text, mineral teal and cinnabar evidence tabs, soft side-window light, scholarly archive atmosphere, no people, no logo, no watermark, no identity data.

Final original-pixel inspection: blank envelope, unlettered circular seal, empty checklist geometry, plain tabs and unmarked book spines. No apparent text, logos, people, watermark or identity data. Accepted first output: `exec-53341378-14dd-48a6-b855-d5267696ece7`.

### campus-route.png

> 16:9 cinematic architectural corridor of a fictional campus, map-like bands of light tracing several possible routes, archive-paper and deep-ink palette with restrained brass highlights, atmospheric but realistic, no people, no sign, no logo, no recognizable university architecture, no readable text.

Final original-pixel inspection: imagined colonnade, abstract circular ornaments and branching light paths. No apparent letters, signs, logos, people, watermark or identifiable institution. Accepted first output: `exec-73da7168-7fe4-410c-bab7-8912b2a02e7b`.

Four independent built-in calls total: two hero attempts, one materials image, one campus image. No collages, crops, overlays or raster edits were used to hide rejected content. Inspection is an agent visual review, not a claim of independent human approval.

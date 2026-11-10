# Architecture decision record — InkFlow v0

## Product boundaries

A handwriting *scan* records deposited ink. A handwriting *trajectory* records the pen path through time. Recovering the latter from the former is an inverse problem with multiple valid explanations: crossbars, crossings, retraces, stroke order, writing direction, pressure, and pen lifts can be unidentifiable. Architecture must expose uncertainty and hypotheses.

Separate the **inverse renderer** (image -> latent traces) from the **forward renderer** (latent traces -> image). Ensure each output can be reconstructed from the source observations with explicit error metrics.

## Services / modules

| Module | Input | Output | Method initially |
|---|---|---|---|
| ingest | PNG/JPEG/TIFF/PDF pages, metadata | calibrated grayscale and color planes | orientation, crop, perspective, lighting and dewarp |
| segment | cleaned page, optional transcript | lines, words, connected components, alignment | projections/connected components first, learned segmentation later |
| geometry | ink masks | distance transform, boundaries, centerline graph | thresholding, medial axis, pruning |
| infer | graph, optional online traces / transcript | candidate ordered strokes + probabilities | graph traversal candidates, junction and curvature costs, differentiable fitting |
| style | accepted strokes and aligned text | glyph variants, transition models, style distributions | hierarchical statistical model before neural generator |
| layout | Unicode text, style model, seed | glyph/allograph sequence, connections, positioning | HarfBuzz for compiled fonts; native context-aware layout in procedural path |
| render | ordered strokes + brush model | SVG/raster/vector sequences/animation | variable-width Bézier strokes and brush deposition |
| export | style model | UFO/OTF/TTF, SVG, PNG, animations | fontTools, ufo2ft/fontmake |
| editor | source, candidates, confidence | curated style model | overlay, graph edit, pen-order correction, compare rendered image |

All modules should be runnable headlessly for reproducible research and via an interactive UI. Heavy learning is optional.

## The crucial abstractions

- **Ink observation**: source image + transformations + masks + provenance.
- **Stroke hypothesis**: oriented continuous centerline, variable width, optional estimated pressure/velocity, uncertainty, and evidence links. A hypothesis is **not** a claim that the original pen followed this exact path.
- **Allograph**: one of several forms of a grapheme in a given context.
- **Transition**: geometry of joins between adjacent units, with exit/entry ports and inter-letter pen-up decision.
- **Writer style**: distributions over slant, widths, height, spacing, baseline wobble, curvature, allographs, and transition choice. Condition on previous/next letters and positional context.
- **Render seed**: explicit, stable random input for deterministic previews and exports.

## Why two rendering backends?

**Procedural path:** supports per-occurrence stochastic variation, connected writing across glyph boundaries, explicit pressure maps, animated pen traces, and a style grammar. It is more expressive but requires our runtime.

**Standard font path:** shapes in ordinary apps, but cannot execute arbitrary procedural or stochastic algorithms. It can approximate variability via GSUB `calt` / `liga` / `rlig`, multiple glyphs, and supported variation axes. Variable-font axes interpolate compatible masters; they do not recover original motion or make arbitrary runtime randomness portable.

Standard font export is a lowering pass of the style model, not the internal representation.

## Implementation arrangement

```text
packages/
  inkflow-core/         Python reference pipeline (Phase 1)
  inkflow-geometry/     optional future optimized Rust crate
  inkflow-render/       procedural runtime / WASM target (later)
  inkflow-font/         font compiler (later)
apps/
  studio/               desktop-capable web UI (later)
docs/
  research/
  architecture/
  plans/
tests/
examples/
assets/                 only license-cleared tiny fixtures
```

For now only create the reference pipeline folder. Don't scaffold empty web monorepos, GPU kernels, and services before evidence of need.

## Interfaces

- Persist artifacts between stages; each has schema version, content hashes, coordinate spaces, image transforms, and source identifiers.
- Stage outputs are immutable; editor corrections are separate overlays with author/date and can be replayed.
- Geometry in normalized page/line local coordinates; renderer converts to pixels/typographic units later.
- Expose plugin interfaces for segmentation, stroke inference, renderer brush, and font export.
- Keep ML weights and datasets external; manifest includes trained model identifier/version and license information.

## Failure modes and handling

1. **Crossings / junctions**: retain multiple topologies, compare forward render.
2. **Overlapping connected cursive characters**: segment by candidate paths and transcript alignment rather than forcing one bounding box per glyph.
3. **Single-sample unseen glyph**: request more examples or surface low-confidence synthetic guess; never silently claim faithful recovery.
4. **Pencil/paper/lighting artifacts**: preserve color image and multiple threshold hypotheses.
5. **Detached diacritics and dots**: model independently and link to a base character.
6. **Stroke thickness not equal to pressure**: estimate brush/nib effects and distinguish observed width from inferred pressure.
7. **Multi-script input**: script-specific segmentation/shape rules and evaluation; Latin handwriting first.

## Benchmarks and checkpoints

- Phase 1: calibrated input and image/ink mask overlays, deterministic reproducibility.
- Phase 2: skeleton and width-field reconstruction, annotated junction graph.
- Phase 3: reconstructions from synthetic known stroke trajectories; quantify topology correctness, pen-lift F1, direction and ordering accuracy (where ground truth exists), reconstruction pixel error.
- Phase 4: 30+ real writer samples per studied glyph where possible; evaluate hold-out glyph images, context joins, legibility, writer preference.
- Phase 5: font shaping compatibility across HarfBuzz and OS renderers; compare procedural vs static outputs.

## Decisions requiring later evidence

Rust versus Python geometry implementation; OCR model; diffusion or sequence-model training; whether segmentation-free paragraph-level generation is worthwhile; editor framework; distribution format for an optional runtime.

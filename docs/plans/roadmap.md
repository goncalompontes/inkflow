# Roadmap and executable research plan

All milestones are prospective; none of the feature implementations below is complete.

## M0 — research and project foundation (current)

- [x] Initialize local git repo and main branch.
- [x] Record conceptual architecture and baseline tooling.
- [x] Identify inverse-problem uncertainty and procedural/font export distinction.
- [ ] Choose license, establish dataset permissions and evaluation annotation rules.
- [ ] Select initial benchmark and write synthetic stroke fixture generator.

**Exit:** reproducible experiment design, dataset licenses verified, metrics defined.

## M1 — image baseline

- [ ] CLI `inkflow ingest INPUT --out RUN_DIR`: validate/normalize scans and EXIF orientation, create manifests.
- [ ] Otsu/Sauvola/adaptive threshold candidates, de-noise and dewarp.
- [ ] Segment lines/components with source-coordinate provenance.
- [ ] Save diagnostic SVG/PNG overlays and snapshots; add golden regression tests.

**Exit:** deterministic pipeline works on clean printed and handwritten pages without requiring GPU.

## M2 — geometry and stroke candidates

- [ ] Distance transform, skeleton thinning, junction graph.
- [ ] Reject spurs while preserving terminals/dots/diacritics.
- [ ] Fit splines and width profiles; generate multiple crossings and stroke direction candidates.
- [ ] Forward-render hypotheses; compare to original observations.
- [ ] Add human correction format and editor-independent CLI.

**Exit:** known synthetic curves and basic real handwritten letters reconstruct well; ambiguous cases flagged.

## M3 — personalized handwriting model

- [ ] Collect consented multiple allographs for every glyph; align transcripts to examples.
- [ ] Estimate baseline, scale, slant, spacing, width, and transition distributions.
- [ ] Context-conditioned variant selection and join geometry.
- [ ] Seeded paragraph generator + stroke-order animation.

**Exit:** legible held-out words, plausible variation, manual editability, deterministic seeds.

## M4 — font output

- [ ] Export UFO masters and static OTF/TTF.
- [ ] Generate multiple alternates and contextual substitutions; validate with HarfBuzz.
- [ ] Test optional parametric axes only when master topology is compatible.
- [ ] Cross-platform rendering regression.

**Exit:** readable output in common desktop applications, with documented differences from procedural engine.

## M5 — learned inverse reconstruction / synthesis

- [ ] Train on **online** pen traces rendered as synthetic offline scans, including known stroke-order labels.
- [ ] Benchmark topology, direction/ordering, scan reconstruction, legibility, writer-style fidelity.
- [ ] Evaluate probabilistic inference and differentiable rasterization against the classical baseline.
- [ ] Add confidence calibration, abstention and editor review for uncertain motion.
- [ ] Investigate sequence models or diffusion conditioned on text, style and neighboring letter states.

**Exit:** demonstrated improvement over baseline on held-out writers, not merely attractive samples.

## M6 — end-user studio

- [ ] Drag-and-drop scans, image rectification, annotations/transcription.
- [ ] Inspect ink mask, skeleton, stroke graph, inferred pen path and confidence.
- [ ] Edit strokes, joins, ports and style distributions.
- [ ] Text playground with stable seed and animation.
- [ ] Export procedural project, SVG, and compiled font; local-only mode.

**Exit:** a user can build and export a personal handwriting style without writing code.

## First three prototype experiments

1. **Controlled synthetic inverse test:** render known vector pen paths with width and crossing variations; recover paths using skeleton + junction solver. Report topology accuracy, mean curve distance and uncertainty.
2. **Offline clean scan test:** collect permissioned 300–600 dpi handwriting on plain paper with known transcript; test adaptive threshold, line segmentation and forward-render pixel error; show failures at crossings.
3. **Online/offline paired test:** acquire consented tablet traces and rasterize them as scans; use true timing only for evaluation, not to cheat offline reconstruction. Compare graph-based solver to learned baseline.

Decision gate after these experiments: only optimize or train models for identified accuracy bottlenecks.

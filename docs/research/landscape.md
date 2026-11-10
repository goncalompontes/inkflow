# Technical research landscape (10 November 2026)

## Problem taxonomy

- **Typography outlines** are closed boundaries; readily vectorized, but no guaranteed pen centerline.
- **Monoline handwriting / lettering** can often be approximated by skeletons and variable-width traces.
- **Brush and calligraphy** are more difficult: nib angle, pressure, pigment spread and stroke overlaps all influence appearance.
- **Connected cursive** requires modeling transitions jointly with letters; character-local segmentation alone loses motion context.
- **Online handwriting** has timestamps, positions and sometimes pressure/tilt; **offline handwriting** gives only final images. Do not conflate their ground truth.

## Candidate methods

| Method | What it helps | What it cannot infer reliably |
|---|---|---|
| Adaptive threshold + denoise + morphological ops | isolate ink and paper | recover timing/pressure |
| Distance transform + medial axis / thinning | centerline, approximate local thickness | choose stroke order at junctions |
| Contours / Bézier vectorization | accurate glyph outlines | reconstruct writing process |
| Skeleton graph search with curvature, continuity and pen-lift priors | plausible traversals at intersections | guarantee the historical path |
| Synthetic render + inverse fit (differentiable or search) | fit strokes to scanned appearance | disambiguate identical rendered paths |
| Transcript-aligned HTR/OCR | segment and label sample regions | provide trustworthy labels without review |
| Hierarchical writer-conditioned statistical model | allographs, slant, spacing, joins | generate unseen letters faithfully without examples |
| Sequence models / diffusion | generative motion and style priors | source-grounded certainty, easy editing, low data demand |

A staged hybrid is preferable to an immediate large end-to-end network.

## Existing libraries and systems

**Image processing**
- [OpenCV](https://docs.opencv.org/) — geometric calibration, binarization, contours, distance transforms.
- [scikit-image skeletonize](https://scikit-image.org/docs/stable/auto_examples/edges/plot_skeleton.html) — morphology, thinning, medial axes for reference geometry.
- [SciPy](https://docs.scipy.org/doc/scipy/) — optimization, interpolation, graph/geometry support.
- [Potrace](https://potrace.sourceforge.net/) — image-to-outline vectorization; useful as a strong **outline** baseline, not a motion detector.

**Fonts and shaping**
- [fontTools](https://fonttools.readthedocs.io/en/latest/) — `fontBuilder`, `ttLib`, UFO, OpenType features, `varLib`.
- [ufo2ft](https://github.com/googlefonts/ufo2ft) / [fontmake](https://github.com/googlefonts/fontmake) — compile source UFO/designspace fonts to binaries.
- [HarfBuzz](https://harfbuzz.github.io/) — Unicode-to-positioned-glyph shaping, testing contextual substitution and font export.
- [OpenType registered features](https://learn.microsoft.com/en-us/typography/opentype/spec/features_ae) — e.g. `calt` and other substitutions for alternate forms.
- [DrawBot](https://github.com/typemytype/drawbot) — optional Python-based typographic drawing experiments.

**Inverse graphics and generative models**
- [diffvg](https://github.com/BachiLi/diffvg) — differentiable rasterization, promising for fitting vector geometry against scanned pixels; benchmark build friction.
- [Graves, Generating Sequences with RNNs (2013)](https://arxiv.org/abs/1308.0850) — foundational example of generating handwriting-like sequences; architecture is historical rather than automatically the best modern solution.
- [PyTorch](https://pytorch.org/) — reference training/inference; CPU pipeline should work without it.

## Important interoperability boundaries

- TTF/OTF glyph outlines are not temporal pen trajectories.
- OpenType GSUB alternates and ligatures offer discrete conditional variation; variable fonts interpolate compatible masters. Neither means unconstrained arbitrary randomness, dynamic physical ink, or whole-word procedural strokes.
- An InkFlow runtime can generate text as strokes and rasterize/animate them; static font export will necessarily approximate some of its richer behavior.
- Brush reconstruction should explicitly distinguish **observed stroke width** from **inferred pressure** and **pen shape**; mapping them one-to-one is physically unsound.

## Suggested language and stack comparison

| Option | Best role | Main tradeoff |
|---|---|---|
| Python | offline vision, optimization, training, font engineering | slow pure-Python loops; vectorize or compile kernels |
| Rust | core graph algorithms, deterministic procedural renderer, WASM | premature complexity for experimental science |
| C++ | existing OpenCV / high-performance raster integrations | ownership complexity and heavier build |
| TypeScript | interactive studio and browser rendering | not ideal for model training |
| Swift/Kotlin | native end-user clients later | lower early research leverage |

**Recommendation:** Python first with strict intermediate schemas and golden fixtures, TypeScript UI later, Rust only around measured hotspots and portable runtime needs.

## Research gaps needing concrete validation

1. How often does skeletonization produce a stable topology across binarization/lighting perturbations?
2. Can junction ordering be inferred using local curvature alone or does it require learned global priors?
3. How much writer data is necessary to learn connected allographs across adjacent letters?
4. Which training datasets legally permit redistribution and derived style generation?
5. How faithful is generated output to a specific writer on **held-out** words and scripts?
6. How do animated stroke sequences compare with paired online ground truth, and how should ambiguity be displayed?

## Dataset shortlist — **investigate licenses before download/use**

IAM offline handwriting, IAM-OnDB online paired trajectories, CVL, RIMES, Bentham, and synthetic traces rendered from permissioned vector strokes. Dataset availability, terms, academic restrictions and commercial permissions must be validated separately; do not assume download implies training redistribution rights.

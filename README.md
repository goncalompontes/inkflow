# InkFlow

**Recover personal handwriting as an editable, procedural writing model from scanned pages, photographs, or other handwriting samples.**

> Status: early deterministic **geometry prototype** with a standalone visual debugger. Writer-specific trajectory inference, procedural text synthesis, and font compilation remain future work.

## Why not just trace characters?

A static handwritten font records letter outlines and repeats them. InkFlow aims to reconstruct a writer-specific **generative process**: pen trajectories, widths and pressure proxies, letter allographs, connections, spacing, baseline movement, and local context. A photograph gives the final deposited ink, not time order; stroke recovery is inherently ambiguous, so InkFlow records hypotheses and confidence rather than pretending ground-truth pen motion was observed.

## Outputs

1. **InkFlow Style Model**: editable, versioned procedural strokes, glyph variants, transitions, style statistics, and uncertainty.
2. **Procedural renderer**: reproducible seeded layout and strokes, with optional animation, SVG/vector, and raster export.
3. **Compiled font**: static TTF/OTF first; contextual alternates, ligatures, and variable fonts where supported. Standard OpenType is not a general-purpose arbitrary stochastic stroke renderer.

## Core pipeline

```text
Images / scans (+ optional transcripts, online pen traces)
  -> calibration & cleanup
  -> segmentation / alignment
  -> ink geometry and skeleton graph
  -> candidate stroke topology and order inference
  -> glyph / ligature / writer-style learning
  -> canonical editable stroke model
        -> procedural text shaping + renderer
        -> font compiler (OpenType)
        -> interactive editor + uncertainty viewer
```

The process supports human-in-the-loop edits and preserves provenance for each inferred segment. Avoid treating OCR output as a verified transcription.

## Proposed stack

- **Research / offline training**: Python 3.11+, OpenCV, scikit-image, NumPy/SciPy, PyTorch as needed.
- **Font tooling**: fontTools, UFO, ufo2ft/fontmake, HarfBuzz for shaping.
- **Geometry core**: Python reference first; Rust only after profiling, exposed to Python via PyO3 and to a web UI via WASM if useful.
- **Editor**: TypeScript + browser canvas/SVG, with a backend API when batch processing or training is required.
- **Data**: versioned JSON manifest + arrays/binary for heavy geometry. Source images remain user-controlled, not committed by default.

See [architecture](docs/architecture/overview.md), [research](docs/research/landscape.md), [roadmap](docs/plans/roadmap.md), and [model contract](docs/architecture/style-model.md).

## Non-goals of first release

- Perfect recovery of actual historical pen velocity/order from a single static image.
- Automatic reconstruction of every unseen character from only a few samples.
- Custom OpenType extensions that conventional operating systems cannot read.
- Training large generative models before establishing deterministic baselines.

## Development

The first prototype has two runtime dependencies: NumPy and Pillow. In the repository root:

```bash
python -m pip install -e .
python examples/make_sample.py
python -m inkflow_core examples/synthetic-sample.png --out runs/demo
python -m unittest discover -s tests -v
```

Open `runs/demo/index.html` in a browser. The standalone inspector embeds its images and graph, so it needs no web server. Select a stage, adjust overlay opacity, toggle graph annotations, inspect pixel/node coordinates, or download the graph JSON. On the **trajectories** stage, select a junction and a ranked pairing to compare alternative colored path partitions live. `runs/demo` also contains separate stage PNG files, `graph.svg`, and `run.json` for headless tooling.

Stages: input, grayscale, threshold, cleaned mask, approximate distance transform, components, skeleton, graph, trajectory hypotheses, width-aware reconstruction, and reconstruction difference. The CLI also supports `--threshold`, `--min-area`, `--max-side`, and `--invert`. Use `--min-area 1` to preserve tiny isolated marks. Image downscaling defaults to a 1000px longest side; use `--max-side 0` to disable it.

The distance transform is a dependency-light approximation. Junction pairing ranks local tangent continuity and width similarity, enumerating up to four hypotheses for degrees 3–8; nodes with larger degree remain explicitly unsupported. These are **local**, not globally ranked hypotheses. Choosing a pairing changes the undirected path partition, not historical pen movements. The candidate graph does **not** recover writing order, direction, pen lifts, historical pressure, or calibrated confidence. Current global thresholding can fail under uneven illumination, and edge width rendering can miss ink at intersections. `ink_iou` measures overlap with cleaned pixels only—not correct trajectory inference. Results are local and ignored by Git; do not commit personal handwriting samples without consent.

## Privacy and rights

Handwriting may be personally identifying. Only process samples you have permission to use. Keep raw samples private by default, support removal and local-only processing, and never infer authorship as a verified identity.

## License

Not yet selected; do not assume this repository is open-source licensed until an explicit license is added.

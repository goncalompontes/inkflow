# InkFlow style model — proposed contract (not implemented)

Versioned writer-specific, content-addressed model; support upgrades and schema validation before persistence.

```json
{
  "schema_version": "0.1-draft",
  "style_id": "sample-style",
  "units": "normalized-em",
  "provenance": [{"source_id": "scan-001", "consent": "owner-supplied"}],
  "metrics": {"baseline": 0, "x_height": 0.48, "cap_height": 0.72, "ascender": 0.78, "descender": -0.22},
  "glyphs": {
    "a": [
      {
        "variant_id": "a-01",
        "context": {"position": "medial"},
        "strokes": [
          {
            "points": [[0.03, 0.1], [0.08, 0.25], [0.2, 0.45]],
            "widths": [0.04, 0.06, 0.05],
            "timing_known": false,
            "direction_confidence": 0.25,
            "source_span_ids": ["span-1"]
          }
        ],
        "entry_port": [0.03, 0.1],
        "exit_port": [0.24, 0.0],
        "confidence": 0.55
      }
    ]
  },
  "style_distributions": {
    "slant_deg": {"mean": 8, "std": 2},
    "baseline_offset": {"mean": 0, "std": 0.015}
  },
  "connections": [],
  "render": {"seed": 1234, "brush": {"kind": "variable-width"}}
}
```

Values above are illustrative only. In implementation, represent trajectories with cubic Bézier segments or fitted splines, arc-length parameterization, variable nib geometry, and optionally samples of pressure/time. Store metadata that discriminates *measured* from *inferred* attributes. User edits must be traceable. Unicode strings may be multi-codepoint clusters; do not assume one code point == one glyph.

## Dataset policy

Data splits must be by **writer** for generalization evaluation, and by **page / word** for adaptation evaluation. Don't allow text or page leakage between training and held-out samples. Online (time-series) pen data supplies true stroke order; offline scans alone do not.

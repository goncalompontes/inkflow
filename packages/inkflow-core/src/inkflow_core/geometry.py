"""Deterministic approximations of ink width and centerline coverage.

The chamfer transform is deliberately dependency-light. It is NOT an exact
Euclidean distance transform and its width estimates are only image geometry.
"""
from __future__ import annotations

import numpy as np


def chamfer_distance(mask: np.ndarray) -> np.ndarray:
    """Approximate distance of ink pixels to background, in pixel units.

    Include an implicit one-pixel background border so solid images are finite.
    Uses 8-connected 3/4 chamfer distances (orthogonal=1, diagonal=sqrt(2)).
    """
    h, w = mask.shape
    inf = float(h + w + 4)
    d = np.pad(np.where(mask, inf, 0.0), 1, constant_values=0.0)
    diag = 2 ** .5
    for y in range(1, h + 1):
        for x in range(1, w + 1):
            if d[y, x]:
                d[y, x] = min(d[y, x], d[y - 1, x] + 1,
                              d[y, x - 1] + 1, d[y - 1, x - 1] + diag,
                              d[y - 1, x + 1] + diag)
    for y in range(h, 0, -1):
        for x in range(w, 0, -1):
            if d[y, x]:
                d[y, x] = min(d[y, x], d[y + 1, x] + 1,
                              d[y, x + 1] + 1, d[y + 1, x + 1] + diag,
                              d[y + 1, x - 1] + diag)
    return d[1:-1, 1:-1]


def annotate_widths(edges: list[dict], distance: np.ndarray) -> None:
    for edge in edges:
        radii = [float(distance[y, x]) for x, y in edge["points"]]
        edge["widths_px"] = [round(2 * r, 2) for r in radii]
        edge["mean_width_px"] = round(float(np.mean(edge["widths_px"])), 2) if radii else 0.0
        edge["hypothesis"] = "undirected centerline candidate"
        edge["confidence"] = None  # Confidence requires calibration, not a fabricated number.


def reconstructed_mask(edges: list[dict], shape: tuple[int, int]) -> np.ndarray:
    """Stroke a disk of estimated radius at each sampled graph point."""
    h, w = shape
    reconstructed = np.zeros((h, w), dtype=bool)
    for edge in edges:
        for (x, y), width in zip(edge["points"], edge["widths_px"]):
            radius = max(.5, width / 2)
            r = int(np.ceil(radius))
            y0, y1 = max(0, y-r), min(h, y+r+1)
            x0, x1 = max(0, x-r), min(w, x+r+1)
            yy, xx = np.ogrid[y0:y1, x0:x1]
            reconstructed[y0:y1, x0:x1] |= (xx-x)**2 + (yy-y)**2 <= radius**2
    return reconstructed


def mask_metrics(original: np.ndarray, reconstructed: np.ndarray) -> dict:
    intersection = int(np.count_nonzero(original & reconstructed))
    union = int(np.count_nonzero(original | reconstructed))
    return {"ink_iou": round(intersection / union, 4) if union else 1.0,
            "false_positive_pixels": int(np.count_nonzero(reconstructed & ~original)),
            "missed_ink_pixels": int(np.count_nonzero(original & ~reconstructed))}

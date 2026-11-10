"""Explainable offline-ink geometry baseline.

No writing order, historical pressure, or direction is recovered by this module.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from .geometry import chamfer_distance, annotate_widths, reconstructed_mask, mask_metrics
from .trajectories import infer_trajectories

NEIGHBORS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
RING = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]


@dataclass
class Analysis:
    source: np.ndarray
    grayscale: np.ndarray
    mask: np.ndarray
    cleaned: np.ndarray
    skeleton: np.ndarray
    distance: np.ndarray
    reconstruction: np.ndarray
    components: list[dict]
    nodes: list[dict]
    edges: list[dict]
    junctions: list[dict]
    paths: list[dict]
    threshold: int
    diagnostics: dict


def load_image(path: str | Path, max_side: int = 1000) -> tuple[np.ndarray, np.ndarray]:
    with Image.open(path) as raw:
        image = ImageOps.exif_transpose(raw).convert("RGB")
        if max_side and max(image.size) > max_side:
            image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        source = np.array(image)
    # Preserve color; convert with luminance weights.
    gray = np.rint(source[..., 0] * .2126 + source[..., 1] * .7152 + source[..., 2] * .0722).astype(np.uint8)
    return source, gray


def otsu_threshold(gray: np.ndarray) -> int:
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = int(gray.size)
    if not total:
        return 127
    means = np.cumsum(hist * np.arange(256))
    counts = np.cumsum(hist)
    valid = (counts > 0) & (counts < total)
    between = np.full(256, -1.0)
    between[valid] = ((means[-1] * counts[valid] - means[valid] * total) ** 2 /
                      (counts[valid] * (total - counts[valid])))
    return int(np.argmax(between))


def components_of(mask: np.ndarray, connectivity: int = 8) -> list[dict]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    offsets = NEIGHBORS if connectivity == 8 else [(-1, 0), (0, -1), (0, 1), (1, 0)]
    parts = []
    for y, x in np.argwhere(mask):
        y, x = int(y), int(x)
        if seen[y, x]:
            continue
        q = deque([(y, x)])
        seen[y, x] = True
        coords = []
        minx = maxx = x
        miny = maxy = y
        while q:
            cy, cx = q.popleft()
            coords.append((cy, cx))
            minx, maxx = min(minx, cx), max(maxx, cx)
            miny, maxy = min(miny, cy), max(maxy, cy)
            for dy, dx in offsets:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        parts.append({"bbox": [minx, miny, maxx + 1, maxy + 1], "area": len(coords), "pixels": coords})
    return sorted(parts, key=lambda p: (p["bbox"][1], p["bbox"][0]))


def remove_small_components(mask: np.ndarray, minimum_area: int) -> tuple[np.ndarray, list[dict], int]:
    components = components_of(mask)
    cleaned = np.zeros_like(mask)
    retained = []
    removed = 0
    for part in components:
        if part["area"] < minimum_area:
            removed += 1
            continue
        ys, xs = zip(*part["pixels"])
        cleaned[ys, xs] = True
        retained.append({k: v for k, v in part.items() if k != "pixels"})
    return cleaned, retained, removed


def skeletonize(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """Zhang-Suen thinning using NumPy; border treated as background."""
    a = np.pad(mask.astype(np.uint8), 1)
    rounds = 0
    # Two substeps per round until convergence.
    while True:
        changed = False
        for step in range(2):
            p2 = a[:-2, 1:-1].astype(bool)
            p3 = a[:-2, 2:].astype(bool)
            p4 = a[1:-1, 2:].astype(bool)
            p5 = a[2:, 2:].astype(bool)
            p6 = a[2:, 1:-1].astype(bool)
            p7 = a[2:, :-2].astype(bool)
            p8 = a[1:-1, :-2].astype(bool)
            p9 = a[:-2, :-2].astype(bool)
            center = a[1:-1, 1:-1].astype(bool)
            p = (p2, p3, p4, p5, p6, p7, p8, p9)
            degree = sum(v.astype(np.uint8) for v in p)
            transitions = sum((~p[i] & p[(i + 1) % 8]).astype(np.uint8) for i in range(8))
            if step == 0:
                condition = ~(p2 & p4 & p6) & ~(p4 & p6 & p8)
            else:
                condition = ~(p2 & p4 & p8) & ~(p2 & p6 & p8)
            deletable = center & (degree >= 2) & (degree <= 6) & (transitions == 1) & condition
            if np.any(deletable):
                a[1:-1, 1:-1][deletable] = 0
                changed = True
        rounds += 1
        if not changed:
            break
    return a[1:-1, 1:-1].astype(bool), rounds


def graph_of(skel: np.ndarray) -> tuple[list[dict], list[dict]]:
    """Compress pixel skeleton into nodes and undirected edge polylines.

    Degree is computed in an 8-neighborhood; diagonal touching can introduce
    spurious junctions. Adjacent junction pixels are therefore clustered.
    """
    pixels = {(int(y), int(x)) for y, x in np.argwhere(skel)}
    if not pixels:
        return [], []

    def nearby(p):
        y, x = p
        return [(y + dy, x + dx) for dy, dx in NEIGHBORS if (y + dy, x + dx) in pixels]

    neighbors = {p: nearby(p) for p in pixels}
    special = {p for p in pixels if len(neighbors[p]) != 2}
    # Every disconnected cycle needs its own anchor, even when other components
    # contain endpoints. Otherwise its entire loop disappears from the graph.
    remaining = set(pixels)
    while remaining:
        seed = min(remaining)
        stack = [seed]
        remaining.remove(seed)
        region = {seed}
        while stack:
            current = stack.pop()
            for other in neighbors[current]:
                if other in remaining:
                    remaining.remove(other)
                    region.add(other)
                    stack.append(other)
        if not (region & special):
            special.add(seed)
    regions = []
    while special:
        seed = min(special)
        q = [seed]
        special.remove(seed)
        region = []
        while q:
            current = q.pop()
            region.append(current)
            for other in neighbors[current]:
                if other in special:
                    special.remove(other)
                    q.append(other)
        regions.append(sorted(region))
    node_for = {}
    nodes = []
    for idx, region in enumerate(sorted(regions, key=lambda r: r[0])):
        cy = float(np.mean([p[0] for p in region]))
        cx = float(np.mean([p[1] for p in region]))
        kind = "junction" if any(len(neighbors[p]) > 2 for p in region) else "endpoint"
        if len(region) == 1 and len(neighbors[region[0]]) == 0:
            kind = "isolated"
        nodes.append({"id": idx, "point": [round(cx, 2), round(cy, 2)], "kind": kind, "pixels": len(region)})
        for p in region:
            node_for[p] = idx

    # Mark each unordered pixel connection exactly once.
    visited = set()

    def key(a, b):
        return (a, b) if a < b else (b, a)

    edges = []
    for start in sorted(node_for):
        for step in neighbors[start]:
            if node_for.get(step) == node_for[start] or key(start, step) in visited:
                continue
            path = [start]
            previous, current = start, step
            visited.add(key(previous, current))
            while True:
                path.append(current)
                if current in node_for:
                    break
                nexts = [p for p in neighbors[current] if p != previous]
                if not nexts:
                    # Defensive: malformed graph; capture dangling endpoint.
                    break
                following = sorted(nexts)[0]
                if key(current, following) in visited:
                    break
                visited.add(key(current, following))
                previous, current = current, following
            if current not in node_for:
                # Should not happen on degree-2 chains.
                continue
            if len(path) >= 2:
                edges.append({"id": len(edges), "start": node_for[start],
                              "end": node_for[current],
                              "points": [[x, y] for y, x in path],
                              "length_px": round(float(sum(np.hypot(
                                  b[1] - a[1], b[0] - a[0]) for a, b in zip(path, path[1:]))), 2),
                              "direction_known": False, "sequence_known": False,
                              "ambiguous": nodes[node_for[start]]["kind"] == "junction"
                              or nodes[node_for[current]]["kind"] == "junction"})
    return nodes, edges


def analyze(source: np.ndarray, gray: np.ndarray, *, threshold: int | None = None,
            minimum_area: int = 3, invert: bool = False) -> Analysis:
    threshold = otsu_threshold(gray) if threshold is None else int(threshold)
    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be between 0 and 255")
    # Inclusive allows perfect black ink; strict works better for Otsu at zero.
    mask = gray <= threshold if threshold else gray == 0
    if invert:
        mask = ~mask
    cleaned, components, removed = remove_small_components(mask, minimum_area)
    skeleton, iterations = skeletonize(cleaned)
    nodes, edges = graph_of(skeleton)
    distance = chamfer_distance(cleaned)
    annotate_widths(edges, distance)
    junctions, paths = infer_trajectories(nodes, edges)
    reconstruction = reconstructed_mask(edges, cleaned.shape)
    metrics = mask_metrics(cleaned, reconstruction)
    return Analysis(source, gray, mask, cleaned, skeleton, distance, reconstruction, components, nodes, edges, junctions, paths, threshold,
                    {"dimensions": [int(gray.shape[1]), int(gray.shape[0])],
                     "raw_ink_pixels": int(mask.sum()), "clean_ink_pixels": int(cleaned.sum()),
                     "skeleton_pixels": int(skeleton.sum()), "components": len(components),
                     "removed_components": removed, "nodes": len(nodes), "edges": len(edges),
                     "ambiguous_edges": sum(int(e["ambiguous"]) for e in edges),
                     "junction_hypotheses": len(junctions),
                     "alternative_pairings": sum(len(j["alternatives"]) for j in junctions),
                     "primary_candidate_paths": len(paths),
                     "thinning_iterations": iterations,
                     "distance_algorithm": "approximate 8-connected chamfer transform",
                     "mean_candidate_width_px": round(float(np.mean([e["mean_width_px"] for e in edges])), 2) if edges else 0.0,
                     **metrics,
                     "warning": "Edge direction/order/pressure are unknown; edges are only candidate centerline segments."})

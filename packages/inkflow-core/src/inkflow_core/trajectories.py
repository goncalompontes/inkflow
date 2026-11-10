"""Explainable hypothetical continuation paths through skeleton junctions.

Ranks are geometric costs, not probabilities or historical writing sequences.
"""
from __future__ import annotations

from functools import lru_cache
from math import acos, pi
import numpy as np


def _ports(nodes: list[dict], edges: list[dict]) -> dict[int, list[dict]]:
    ports = {node["id"]: [] for node in nodes}
    for edge in edges:
        points = edge["points"]
        if len(points) < 2:
            continue
        for side in ("start", "end"):
            oriented = points if side == "start" else points[::-1]
            tip = np.asarray(oriented[0], dtype=float)
            # A self-loop can return to its starting point within the sample
            # window. Use the furthest non-coincident nearby point instead.
            samples = [np.asarray(p, dtype=float) for p in oriented[1:5]]
            v = max((sample - tip for sample in samples),
                    key=lambda candidate: float(np.linalg.norm(candidate)))
            norm = float(np.linalg.norm(v))
            if norm < 1e-9:
                continue
            widths = edge.get("widths_px", [])
            ports[edge[side]].append({
                "edge": edge["id"], "side": side,
                "vector": [float(v[0] / norm), float(v[1] / norm)],
                "width": float(widths[0 if side == "start" else -1]) if widths else None
            })
    for group in ports.values():
        group.sort(key=lambda p: (p["edge"], p["side"]))
    return ports


def _pair_cost(a: dict, b: dict) -> float:
    dot = float(np.clip(np.dot(a["vector"], b["vector"]), -1, 1))
    bend = acos(-dot) / pi
    wa, wb = a["width"], b["width"]
    mismatch = abs(wa - wb) / max(wa, wb) if wa and wb else 0
    return round(bend + .15 * mismatch, 6)


def _alternatives(ports: list[dict], limit: int = 4) -> list[dict]:
    """Enumerate exact pairings up to degree eight, leaving one odd arm free."""
    n = len(ports)
    if n < 3:
        return []
    if n > 8:
        return [{"rank": 0, "cost": None, "pairs": [], "unmatched": list(range(n)),
                 "reason": "degree exceeds exact search limit"}]

    @lru_cache(None)
    def match(indices: tuple[int, ...]):
        if not indices:
            return (((), ()),)
        first, *rest = indices
        result = []
        if len(indices) % 2:
            for pairs, unmatched in match(tuple(rest)):
                result.append((pairs, (first,) + unmatched))
        for i, other in enumerate(rest):
            remaining = tuple(rest[:i] + rest[i + 1:])
            for pairs, unmatched in match(remaining):
                result.append((((first, other),) + pairs, unmatched))
        return tuple(result)

    ranked = []
    for pairs, unmatched in match(tuple(range(n))):
        cost = round(sum(_pair_cost(ports[i], ports[j]) for i, j in pairs), 6)
        ranked.append((cost, pairs, unmatched))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    return [{"rank": rank, "cost": cost,
             "pairs": [[i, j] for i, j in pairs], "unmatched": list(unmatched)}
            for rank, (cost, pairs, unmatched) in enumerate(ranked[:limit])]


def trace_paths(edges: list[dict], junctions: list[dict],
                selections: dict[int, int] | None = None) -> list[dict]:
    """Follow selected pairings without reusing an undirected graph edge."""
    selections = selections or {}
    links = {}
    for junction in junctions:
        selection = selections.get(junction["node"], 0)
        if not 0 <= selection < len(junction["alternatives"]):
            raise ValueError(f"Invalid alternative {selection} for junction {junction['node']}")
        for i, k in junction["alternatives"][selection]["pairs"]:
            p, q = junction["ports"][i], junction["ports"][k]
            a, b = (p["edge"], p["side"]), (q["edge"], q["side"])
            links[a], links[b] = b, a
    endpoints = [(edge["id"], side) for edge in edges for side in ("start", "end")]
    seen = set()
    paths = []

    def walk(start):
        port, steps, closed = start, [], False
        while port[0] not in seen:
            edge_id, enter = port
            seen.add(edge_id)
            steps.append({"edge": edge_id, "reversed": enter == "end"})
            opposite = (edge_id, "end" if enter == "start" else "start")
            following = links.get(opposite)
            if following is None:
                break
            if following[0] in seen:
                closed = following == start
                break
            port = following
        if steps:
            paths.append({"id": len(paths), "steps": steps, "closed": closed,
                          "direction_known": False, "order_known": False,
                          "pen_lifts_known": False, "inferred": True})

    for port in endpoints:
        if port not in links and port[0] not in seen:
            walk(port)
    for port in endpoints:
        if port[0] not in seen:
            walk(port)
    return paths


def infer_trajectories(nodes: list[dict], edges: list[dict], *,
                       alternatives: int = 4) -> tuple[list[dict], list[dict]]:
    """Return locally ranked junction options and a primary path partition.

    Options are local, not globally ranked joint hypotheses.
    """
    ports = _ports(nodes, edges)
    junctions = []
    for node in nodes:
        if node["kind"] != "junction":
            continue
        group = ports[node["id"]]
        options = _alternatives(group, alternatives)
        if not options:
            continue
        junctions.append({"node": node["id"], "point": node["point"],
                          "ports": group, "alternatives": options,
                          "ambiguous": len(options) > 1, "confidence": None,
                          "method": "local tangent continuity and width consistency"})
    return junctions, trace_paths(edges, junctions)

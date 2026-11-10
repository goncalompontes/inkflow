"""Deterministic tests for locally ranked ambiguous junction continuations."""
import unittest

from inkflow_core.trajectories import infer_trajectories, _alternatives, trace_paths


def edge(idx, node_a, node_b, points):
    return {"id": idx, "start": node_a, "end": node_b, "points": points,
            "widths_px": [4.0] * len(points)}


class TrajectoryTests(unittest.TestCase):
    def test_four_arm_crossing_prefers_straight_continuations(self):
        nodes = [{"id": i, "kind": "junction" if i == 0 else "endpoint",
                  "point": [10, 10]} for i in range(5)]
        edges = [
            edge(0, 0, 1, [[10, 10], [10, 9], [10, 8], [10, 7], [10, 6]]),
            edge(1, 0, 2, [[10, 10], [11, 10], [12, 10], [13, 10], [14, 10]]),
            edge(2, 0, 3, [[10, 10], [10, 11], [10, 12], [10, 13], [10, 14]]),
            edge(3, 0, 4, [[10, 10], [9, 10], [8, 10], [7, 10], [6, 10]]),
        ]
        junctions, paths = infer_trajectories(nodes, edges)
        self.assertEqual(len(junctions), 1)
        self.assertEqual(junctions[0]["alternatives"][0]["pairs"], [[0, 2], [1, 3]])
        self.assertEqual(junctions[0]["alternatives"][0]["cost"], 0)
        self.assertEqual(len(paths), 2)
        self.assertEqual({s["edge"] for path in paths for s in path["steps"]}, {0, 1, 2, 3})
        self.assertFalse(any(path["direction_known"] for path in paths))
        alternate = trace_paths(edges, junctions, {0: 1})
        self.assertEqual({s["edge"] for path in alternate for s in path["steps"]}, {0, 1, 2, 3})
        self.assertNotEqual(
            {frozenset(step["edge"] for step in p["steps"]) for p in paths},
            {frozenset(step["edge"] for step in p["steps"]) for p in alternate},
        )

    def test_three_arm_junction_has_one_unmatched_arm(self):
        ports = [
            {"vector": [1, 0], "width": 4},
            {"vector": [-1, 0], "width": 4},
            {"vector": [0, 1], "width": 4},
        ]
        options = _alternatives(ports)
        self.assertEqual(len(options), 3)
        self.assertEqual(options[0]["pairs"], [[0, 1]])
        self.assertEqual(options[0]["unmatched"], [2])

    def test_degree_limit_is_explicit(self):
        ports = [{"vector": [1, 0], "width": 4}] * 9
        options = _alternatives(ports)
        self.assertIsNone(options[0]["cost"])
        self.assertEqual(options[0]["pairs"], [])

    def test_loop_edge_keeps_both_ports_and_traces_once(self):
        nodes = [{"id": 0, "kind": "junction", "point": [0, 0]},
                 {"id": 1, "kind": "endpoint", "point": [5, 0]},
                 {"id": 2, "kind": "endpoint", "point": [-5, 0]}]
        edges = [edge(0, 0, 0, [[0, 0], [0, 1], [1, 2], [2, 1], [0, 0]]),
                 edge(1, 0, 1, [[0, 0], [1, 0], [3, 0], [5, 0]]),
                 edge(2, 0, 2, [[0, 0], [-1, 0], [-3, 0], [-5, 0]])]
        junctions, paths = infer_trajectories(nodes, edges)
        self.assertEqual(len(junctions[0]["ports"]), 4)
        self.assertEqual(sum(len(p["steps"]) for p in paths), 3)

    def test_empty_graph(self):
        self.assertEqual(infer_trajectories([], []), ([], []))


if __name__ == "__main__":
    unittest.main()

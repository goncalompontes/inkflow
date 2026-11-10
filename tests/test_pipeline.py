"""Deterministic tests for the baseline geometry pipeline."""
import unittest
import numpy as np
from PIL import Image, ImageDraw

from inkflow_core.pipeline import analyze, graph_of, otsu_threshold, skeletonize, components_of
from inkflow_core.report import make_html
from inkflow_core.geometry import chamfer_distance, reconstructed_mask, mask_metrics


class PipelineTests(unittest.TestCase):
    def test_otsu_and_cleaning(self):
        gray = np.full((50, 60), 255, dtype=np.uint8)
        gray[10:35, 15:20] = 0
        gray[2, 2] = 0
        source = np.repeat(gray[..., None], 3, axis=2)
        a = analyze(source, gray, minimum_area=2)
        self.assertEqual(a.threshold, 0)
        self.assertEqual(a.diagnostics["removed_components"], 1)
        self.assertEqual(len(a.components), 1)
        self.assertGreater(a.diagnostics["skeleton_pixels"], 0)

    def test_single_line_graph(self):
        skel = np.zeros((20, 25), dtype=bool)
        skel[5:16, 12] = True
        nodes, edges = graph_of(skel)
        self.assertEqual(len(edges), 1)
        self.assertEqual(len(nodes), 2)
        self.assertEqual(edges[0]["length_px"], 10)
        self.assertFalse(edges[0]["direction_known"])

    def test_cycle_has_anchor(self):
        skel = np.zeros((12, 12), dtype=bool)
        for y,x in [(4,5),(5,6),(6,5),(5,4)]:
            skel[y,x] = True
        nodes, edges = graph_of(skel)
        self.assertGreaterEqual(len(nodes), 1)
        self.assertGreaterEqual(len(edges), 1)

    def test_cycle_survives_next_to_other_component(self):
        skel = np.zeros((24, 24), dtype=bool)
        skel[3:10, 3] = True
        for y, x in [(15, 16), (16, 17), (17, 16), (16, 15)]:
            skel[y, x] = True
        nodes, edges = graph_of(skel)
        self.assertEqual(len(edges), 2)
        self.assertEqual(len(nodes), 3)

    def test_skeleton_thins_line(self):
        skel, rounds = skeletonize(np.ones((7, 13), dtype=bool))
        self.assertTrue(skel.sum() < 91)
        self.assertTrue(rounds >= 1)

    def test_empty_image(self):
        gray = np.full((10, 10), 255, dtype=np.uint8)
        a = analyze(np.repeat(gray[..., None], 3, axis=2), gray)
        self.assertEqual(len(a.nodes), 0)
        self.assertEqual(len(a.edges), 0)

    def test_chamfer_distance_and_widths(self):
        mask = np.zeros((11, 11), dtype=bool)
        mask[2:9, 2:9] = True
        distance = chamfer_distance(mask)
        self.assertEqual(distance[0, 0], 0)
        self.assertEqual(distance[2, 2], 1)
        self.assertGreater(distance[5, 5], distance[3, 3])

    def test_reconstruction_metrics(self):
        gray = np.full((40, 60), 255, dtype=np.uint8)
        gray[18:23, 8:52] = 0
        a = analyze(np.repeat(gray[..., None], 3, axis=2), gray)
        self.assertTrue(a.edges)
        self.assertTrue(all(len(e["widths_px"]) == len(e["points"]) for e in a.edges))
        self.assertGreater(a.diagnostics["ink_iou"], 0.3)
        self.assertEqual(mask_metrics(a.cleaned, a.cleaned)["ink_iou"], 1)

    def test_self_contained_viewer_escapes_input(self):
        payload = {"images": {"source": "data:image/png;base64,xx"}, "run": {"source_path": "<img>", "diagnostics": {}, "nodes": []}}
        html = make_html(payload["images"], "<svg></svg>", payload["run"])
        self.assertIn("&lt;img&gt;", html)
        self.assertNotIn('src="<img>"', html)


if __name__ == "__main__":
    unittest.main()

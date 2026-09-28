"""Real-binary qualification of function-parallel fresh extraction."""

from __future__ import annotations

import os
import unittest

from extractor.binary_cfg import validate_pinned_cfg
from extractor.binary_inventory import load_pinned_binary
from extractor.fresh_parallel import extract_fresh_functions


class FreshParallelTest(unittest.TestCase):
    def test_extracts_every_root_with_one_available_worker_per_function(self) -> None:
        pinned = load_pinned_binary()
        cfg = validate_pinned_cfg(pinned)
        roots = cfg["roots"]
        worker_count = min(len(roots), os.cpu_count() or 1)

        results = extract_fresh_functions(
            pinned,
            cfg,
            max_workers=worker_count,
        )

        self.assertEqual(set(result.function_id for result in results), set(roots))
        for result in results:
            expected_instructions = sum(
                len(block["instructions"])
                for block in roots[result.function_id]["blocks"]
            )
            self.assertEqual(len(result.occurrences), expected_instructions)
            self.assertGreaterEqual(len(result.local_edges), expected_instructions)
            for edge in result.local_edges:
                edge.summary.validate(result.declarations)

        primitive = pinned.manifest["primitive_boundaries"]["memcpy"]
        handler_targets = {
            edge.summary.target.value
            for result in results
            if result.function_id.endswith("_handler")
            for edge in result.local_edges
            if edge.summary.target.kind == "address"
        }
        self.assertIn(primitive, handler_targets)


if __name__ == "__main__":
    unittest.main()

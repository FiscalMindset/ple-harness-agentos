"""Local harness tests with an in-memory fake session. No Docker, no model needed."""

import asyncio
import json
import unittest

import harness


class FakeSession:
    def __init__(self, instruction, workdir="/app", files=None):
        self.instruction = instruction
        self.workdir = workdir
        self.files = files or {}
        self.written = {}

    async def read_file(self, path):
        key = path.rsplit("/", 1)[-1]
        if key not in self.files:
            raise FileNotFoundError(path)
        data = self.files[key]
        return data.encode() if isinstance(data, str) else data

    async def write_file(self, path, data):
        self.written[path.rsplit("/", 1)[-1]] = data


class HarnessTests(unittest.TestCase):
    def test_steel_deliverable_and_gate(self):
        params = {"span_ft": 20, "w_dead_klf": 0.1, "w_live_klf": 0.2,
                  "zx_in3": 1000, "ix_in4": 20000, "d_in": 30, "tw_in": 1.0}
        s = FakeSession("AISC 360 steel girder sizing", files={"params.json": json.dumps(params)})
        msg = asyncio.run(harness.solve(s))
        report = json.loads(s.written["solution.json"])
        self.assertEqual(report["kind"], "steel")
        self.assertEqual(report["gate"], 1)
        self.assertTrue(report["gate_verification"]["passed"])
        self.assertIn("pre-submission gate verified", msg)

    def test_gate_rejects_fabricated_success(self):
        # A report claiming gate=1 with an impossible ratio must be rejected.
        report = {
            "status": "computed", "kind": "steel", "params": {},
            "result": {"governing": "AISC", "ratios": {"moment": 1e12}}, "gate": 1,
        }
        passed, reason = harness.hard_gate(report)
        self.assertFalse(passed)
        self.assertTrue("does not match" in reason or "non-finite" in reason)

    def test_unknown_task_fails_closed(self):
        s = FakeSession("Please write a poem about bridges", files={})
        msg = asyncio.run(harness.solve(s))
        report = json.loads(s.written["solution.json"])
        self.assertEqual(report["gate"], 0)
        self.assertIn("gate=0", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)

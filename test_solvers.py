"""Known-answer tests for the deterministic solvers. Real numbers, no simulation."""

import math
import unittest

import solvers


class SteelBeamTests(unittest.TestCase):
    def test_uniform_load_hand_calculation(self):
        # span 20 ft, wd 0.5, wl 1.0 klf, Zx 100 in3, Ix 800 in4, d 18, tw 0.5
        r = solvers.steel_beam_lrfd(20, 0.5, 1.0, 100, 800, 18, 0.5)
        wu = 1.2 * 0.5 + 1.6 * 1.0  # 2.2 klf
        self.assertAlmostEqual(r["ratios"]["moment"], (wu * 20**2 / 8 * 12) / (0.9 * 50 * 100))
        self.assertAlmostEqual(r["ratios"]["shear"], (wu * 20 / 2) / (0.9 * 0.6 * 50 * 18 * 0.5))
        # phi*Fy*Zx = 4500 kip-in, demand Mu = 1320 kip-in -> moment ratio 0.293;
        # deflection for Ix=800 in4 on a 20 ft span is the governing check here.
        self.assertAlmostEqual(r["ratios"]["moment"], 1320.0 / 4500.0)

    def test_oversized_section_passes(self):
        r = solvers.steel_beam_lrfd(20, 0.1, 0.2, 1000, 20000, 30, 1.0)
        self.assertTrue(r["compliant"])

    def test_bounds(self):
        with self.assertRaises(ValueError):
            solvers.steel_beam_lrfd(500, 1, 1, 100, 800, 18, 0.5)


class FeederTests(unittest.TestCase):
    def test_125_percent_and_derate(self):
        r = solvers.nec_feeder(100, 480, 100, "1/0", ambient_c=40, conductors=4)
        self.assertAlmostEqual(r["design_current_a"], 100000 / (math.sqrt(3) * 480 * 0.9))
        self.assertAlmostEqual(r["required_a"], 1.25 * r["design_current_a"])
        self.assertAlmostEqual(r["allowable_a"], 150 * 0.94 * 0.8)
        self.assertEqual(r["governing"].startswith("NFPA 70"), True)

    def test_unknown_gauge(self):
        with self.assertRaises(ValueError):
            solvers.nec_feeder(100, 480, 100, "99")


class HydraulicTests(unittest.TestCase):
    def test_darcy_known(self):
        r = solvers.darcy_weisbach_lcc(500, 200, 6)
        self.assertGreater(r["velocity_fps"], 0)
        self.assertGreater(r["reynolds"], 4000)
        self.assertGreater(0.05, r["friction_factor"])
        self.assertGreater(r["lcc_25yr_usd"], 45000)
        self.assertEqual(r["governing"].startswith("Darcy"), True)


class EarthworkTests(unittest.TestCase):
    def test_prismoidal_flat(self):
        r = solvers.earthwork_prismoidal([
            {"area": 100, "mid_area": 100},
            {"area": 100, "mid_area": 100},
        ], 100)
        self.assertAlmostEqual(r["cut_cy"], 10000 / 27)
        self.assertAlmostEqual(r["fill_cy"], 0)
        self.assertFalse(r["balanced"])  # pure cut with zero fill is not balanced


if __name__ == "__main__":
    unittest.main(verbosity=2)

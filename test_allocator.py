"""Automated unit tests for CISC 3320 HW5. Run: python -m unittest -v"""
import unittest
from allocator import MemoryAllocator, run_command


class AllocatorTests(unittest.TestCase):
    def test_lecture_trace_all_policies(self):
        expected = {
            "first": (200, 650, [(480, 20), (750, 250)]),
            "best": (200, 650, [(480, 20), (750, 250)]),
            "worst": (650, 200, [(300, 200), (930, 70)]),
        }
        for policy, (e_address, f_address, final_holes) in expected.items():
            with self.subTest(policy=policy):
                a = MemoryAllocator(1000, policy)
                for name, size in (("A", 200), ("B", 300), ("C", 150), ("D", 100)):
                    a.allocate(name, size)
                a.free("B")
                a.free("D")
                self.assertEqual(a.allocate("E", 280), e_address)
                self.assertEqual(a.allocate("F", 100), f_address)
                with self.assertRaisesRegex(ValueError, "out of memory"):
                    a.allocate("G", 260)
                self.assertEqual([(b.start, b.size) for b in a.blocks if b.free], final_holes)
                self.assertEqual(a.stats()["free"], 270)
                a.check_invariants()

    def test_exact_fit_no_zero_hole(self):
        a = MemoryAllocator(100)
        self.assertEqual(a.allocate("A", 100), 0)
        self.assertEqual(a.stats()["holes"], 0)
        self.assertEqual(a.stats()["fragmentation"], 0)

    def test_coalesce_both_sides(self):
        a = MemoryAllocator(100)
        for name, size in (("A", 20), ("B", 30), ("C", 20), ("D", 30)):
            a.allocate(name, size)
        a.free("A")
        a.free("C")
        a.free("B")
        self.assertEqual([(b.start, b.size) for b in a.blocks if b.free], [(0, 70)])
        a.free("D")
        self.assertEqual([(b.start, b.size) for b in a.blocks if b.free], [(0, 100)])

    def test_invalid_operations_do_not_change_pool(self):
        a = MemoryAllocator(100)
        a.allocate("A", 40)
        for action, error in ((lambda: a.allocate("A", 10), "duplicate"),
                              (lambda: a.allocate("B", 0), "positive"),
                              (lambda: a.allocate("B", 101), "out of memory"),
                              (lambda: a.free("Z"), "unknown")):
            before = a.memory_map()
            with self.assertRaisesRegex(ValueError, error):
                action()
            self.assertEqual(a.memory_map(), before)
        a.free("A")
        before = a.memory_map()
        with self.assertRaisesRegex(ValueError, "double free"):
            a.free("A")
        self.assertEqual(a.memory_map(), before)

    def test_name_reuse_after_free(self):
        a = MemoryAllocator(100)
        a.allocate("A", 10)
        a.free("A")
        a.allocate("A", 20)
        self.assertEqual(a.stats()["used"], 20)

    def test_policy_tie_break_lowest_address(self):
        for policy in ("best", "worst"):
            a = MemoryAllocator(100, policy)
            for name in ("A", "B", "C", "D", "E"):
                a.allocate(name, 20)
            a.free("B")
            a.free("D")
            self.assertEqual(a.allocate("F", 10), 20)

    def test_fragmentation(self):
        a = MemoryAllocator()
        a.allocate("A", 200)
        a.allocate("B", 300)
        a.allocate("C", 150)
        a.free("B")
        s = a.stats()
        self.assertEqual((s["used"], s["free"], s["holes"], s["largest_hole"]), (350, 650, 2, 350))
        self.assertAlmostEqual(s["fragmentation"], 46.1538461538)

    def test_command_errors_and_switching(self):
        a = MemoryAllocator(100)
        self.assertEqual(run_command(a, "policy worst"), "policy: worst-fit")
        self.assertIn("ERROR", run_command(a, "alloc X nope"))
        self.assertIn("ERROR", run_command(a, "policy random"))
        self.assertIn("ERROR", run_command(a, "free X"))
        self.assertIn("pool 100", run_command(a, "stats"))
        self.assertIn("FREE", run_command(a, "map"))

    def test_invalid_pool(self):
        for size in (0, -1):
            with self.assertRaises(ValueError):
                MemoryAllocator(size)


if __name__ == "__main__":
    unittest.main()

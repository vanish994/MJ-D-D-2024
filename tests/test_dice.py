import unittest

from app.services.dice import roll


class DiceUtilityTests(unittest.TestCase):
    def test_roll_is_deterministic_when_random_source_is_injected(self):
        values = iter((0, 19, 5))
        result = roll("3d20-2", randbelow=lambda sides: next(values))
        self.assertEqual(result["formula"], "3d20-2")
        self.assertEqual([die["result"] for die in result["dice"]], [1, 20, 6])
        self.assertEqual(result["total"], 25)

    def test_single_die_and_modifier(self):
        result = roll("d6+3", randbelow=lambda _sides: 4)
        self.assertEqual(result, {
            "formula": "1d6+3",
            "dice": [{"sides": 6, "result": 5}],
            "modifier": 3,
            "total": 8,
        })

    def test_invalid_expressions_and_bounds_are_rejected(self):
        for formula in ("", "d1", "101d6", "1d1001", "1d6+100001", "1d6; import os"):
            with self.subTest(formula=formula), self.assertRaises(ValueError):
                roll(formula, randbelow=lambda _sides: 0)

    def test_random_source_must_return_value_in_range(self):
        with self.assertRaises(RuntimeError):
            roll("1d6", randbelow=lambda _sides: 6)


if __name__ == "__main__":
    unittest.main()

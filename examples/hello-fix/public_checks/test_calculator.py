import unittest

from starter.calculator import add


class CalculatorTests(unittest.TestCase):
    def test_positive_values(self) -> None:
        self.assertEqual(add(2, 3), 5)

    def test_values_that_cancel(self) -> None:
        self.assertEqual(add(-2, 2), 0)


if __name__ == "__main__":
    unittest.main()


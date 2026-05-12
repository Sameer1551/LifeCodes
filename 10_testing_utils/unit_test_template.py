"""
unit_test_template.py
---------------------
Copy-paste ready unit test template using Python's built-in unittest module.
Covers the most common testing patterns you'll use in real projects.

Usage:
    python -m pytest unit_test_template.py -v
    python unit_test_template.py
"""

import unittest
from unittest.mock import MagicMock, patch


# ─── Example: the code you want to test ──────────────────────────────────────
# Replace this with an import of your actual module, e.g.:
#   from mymodule import add, multiply, fetch_data

def add(a, b):
    return a + b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def fetch_data(api_client, endpoint):
    """Example function that calls an external API client."""
    response = api_client.get(endpoint)
    if response.status_code == 200:
        return response.json()
    return None

def process_items(items: list) -> list:
    """Filter out None values and strip strings."""
    return [item.strip() for item in items if item is not None]


# ─── Test Cases ──────────────────────────────────────────────────────────────

class TestMathFunctions(unittest.TestCase):
    """Tests for pure math/logic functions."""

    def test_add_positive_numbers(self):
        self.assertEqual(add(2, 3), 5)

    def test_add_negative_numbers(self):
        self.assertEqual(add(-1, -1), -2)

    def test_add_zero(self):
        self.assertEqual(add(0, 0), 0)

    def test_divide_normal(self):
        self.assertAlmostEqual(divide(10, 4), 2.5)

    def test_divide_by_zero_raises(self):
        with self.assertRaises(ValueError) as ctx:
            divide(5, 0)
        self.assertIn("zero", str(ctx.exception).lower())


class TestProcessItems(unittest.TestCase):
    """Tests for list processing functions."""

    def test_strips_whitespace(self):
        result = process_items(["  hello  ", " world "])
        self.assertEqual(result, ["hello", "world"])

    def test_filters_none_values(self):
        result = process_items(["a", None, "b"])
        self.assertEqual(result, ["a", "b"])

    def test_empty_list_returns_empty(self):
        self.assertEqual(process_items([]), [])

    def test_all_none_returns_empty(self):
        self.assertEqual(process_items([None, None]), [])


class TestWithMocks(unittest.TestCase):
    """
    Tests using mocks — use these when your function calls:
    - External APIs
    - Databases
    - File system
    - Any I/O that shouldn't run in tests
    """

    def test_fetch_data_success(self):
        # Create a fake API client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "Test"}
        mock_client.get.return_value = mock_response

        result = fetch_data(mock_client, "/users/1")

        self.assertEqual(result, {"id": 1, "name": "Test"})
        mock_client.get.assert_called_once_with("/users/1")

    def test_fetch_data_failure_returns_none(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        result = fetch_data(mock_client, "/users/999")
        self.assertIsNone(result)

    @patch("builtins.open")
    def test_patch_builtin(self, mock_open):
        """Example of patching builtins like open()."""
        mock_open.return_value.__enter__ = MagicMock(return_value=MagicMock(read=lambda: "content"))
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        # Your code that uses open() would be tested here
        mock_open.assert_not_called()  # placeholder assertion


class TestSetupTeardown(unittest.TestCase):
    """Tests with setUp and tearDown lifecycle hooks."""

    def setUp(self):
        """Runs BEFORE each test — set up shared state here."""
        self.sample_data = [1, 2, 3, 4, 5]
        self.config = {"debug": True, "max_items": 100}

    def tearDown(self):
        """Runs AFTER each test — clean up resources here."""
        self.sample_data = None

    def test_data_is_list(self):
        self.assertIsInstance(self.sample_data, list)

    def test_config_has_required_keys(self):
        self.assertIn("debug", self.config)
        self.assertIn("max_items", self.config)

    def test_sum_of_data(self):
        self.assertEqual(sum(self.sample_data), 15)


# ─── Common Assertion Cheat Sheet ─────────────────────────────────────────────
# assertEqual(a, b)          → a == b
# assertNotEqual(a, b)       → a != b
# assertTrue(x)              → bool(x) is True
# assertFalse(x)             → bool(x) is False
# assertIsNone(x)            → x is None
# assertIsNotNone(x)         → x is not None
# assertIn(a, b)             → a in b
# assertNotIn(a, b)          → a not in b
# assertRaises(Error, func)  → func raises Error
# assertAlmostEqual(a, b)    → round(a-b, 7) == 0
# assertIsInstance(a, Type)  → isinstance(a, Type)

# ─── Run directly ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)

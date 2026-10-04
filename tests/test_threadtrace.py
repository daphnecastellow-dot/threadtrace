import tempfile
import unittest
from pathlib import Path

from threadtrace import (
    ThreadtraceError,
    add_item,
    add_source,
    change_status,
    load,
    new_trail,
    render_markdown,
    revise_item,
    save,
)


class ThreadtraceTests(unittest.TestCase):
    def test_add_revise_status_and_render(self):
        data = new_trail("Test Trail")
        item_id = add_item(data, "A first claim", "inference", source="Notebook")
        self.assertEqual(item_id, "T001")

        revise_item(
            data,
            "T001",
            "A narrower claim",
            "A counterexample weakened the original wording.",
            status="unresolved",
        )
        add_source(data, "T001", "Primary record", "https://example.com/record")
        change_status(data, "T001", "documented", "Primary record confirmed the narrow claim.")

        item = data["items"][0]
        self.assertEqual(item["claim"], "A narrower claim")
        self.assertEqual(item["status"], "documented")
        self.assertEqual(len(item["history"]), 4)
        self.assertEqual(item["history"][1]["previous_claim"], "A first claim")

        md = render_markdown(data)
        self.assertIn("T001 · documented", md)
        self.assertIn("A first claim", md)
        self.assertIn("A narrower claim", md)
        self.assertIn("Primary record", md)

    def test_round_trip(self):
        data = new_trail("Round Trip")
        add_item(data, "Something happened", "unresolved")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trail.json"
            save(path, data)
            loaded = load(path)
        self.assertEqual(loaded["title"], "Round Trip")
        self.assertEqual(loaded["items"][0]["id"], "T001")

    def test_rejects_bad_status(self):
        data = new_trail("Bad Status")
        with self.assertRaises(ThreadtraceError):
            add_item(data, "Claim", "certain-ish")


if __name__ == "__main__":
    unittest.main()

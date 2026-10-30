"""Check missing targets and fragments without external requests."""
from pathlib import Path
import tempfile
import unittest

from scripts.check_doc_links import check


class DocumentationLinkTests(unittest.TestCase):
    def test_links_fragments_and_fenced_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "# Main\n[valid](doc.md#same-1)\n[external](https://example.invalid/a)\n"
                "```\n[ignored](not-real.md)\n```\n", encoding="utf-8")
            (root / "doc.md").write_text("# Same\n# Same\n", encoding="utf-8")
            self.assertEqual(check(root), [])
            (root / "README.md").write_text(
                "[missing](no.md)\n[fragment](doc.md#absent)\n[escape](../outside.md)\n", encoding="utf-8")
            failures = check(root)
            self.assertEqual(len(failures), 3)
            self.assertTrue(any("missing target" in x for x in failures))
            self.assertTrue(any("missing heading" in x for x in failures))
            self.assertTrue(any("leaves repository" in x for x in failures))


if __name__ == "__main__":
    unittest.main()

import base64
import json
import unittest
from datetime import datetime

from app.pagination import decode_cursor, encode_cursor, parse_page_query


class PaginationParsingTests(unittest.TestCase):
    def test_cursor_roundtrip_preserves_timestamp_and_id(self):
        row = {"created_at": "2026-10-30T08:00:01.123456+00:00",
               "id": "12345678-1234-5678-9234-567812345678"}
        timestamp, identifier = decode_cursor(encode_cursor(row))
        self.assertEqual(timestamp, datetime.fromisoformat(row["created_at"]))
        self.assertEqual(identifier, row["id"])
        self.assertEqual(parse_page_query("")[0], 100)

    def test_rejects_untrusted_or_incomplete_cursor(self):
        for data in ({"t": "2026-01-01T00:00:00", "id": "12345678-1234-5678-9234-567812345678"},
                     {"t": "2026-01-01T00:00:00+00:00", "id": "not-a-uuid"},
                     {"t": "2026-01-01T00:00:00+00:00"},
                     {"t": None, "id": "12345678-1234-5678-9234-567812345678"}):
            token = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
            with self.subTest(data=data), self.assertRaises(ValueError):
                decode_cursor(token)
        for token in ("", "!", "a" * 257, "a", "%%%%"):
            with self.subTest(token=token), self.assertRaises(ValueError):
                decode_cursor(token)

    def test_query_limits_duplicates_and_invalid_values(self):
        for query in ("limit=0", "limit=101", "limit=-1", "limit=1&limit=2", "limit=", "limit=%FF",
                      "cursor=", "x=1", "limit=1&cursor=x&x=1", "x=" + "a" * 513):
            with self.subTest(query=query), self.assertRaises(ValueError):
                parse_page_query(query)
        self.assertEqual(parse_page_query("limit=1"), (1, None))
        self.assertEqual(parse_page_query("limit=100"), (100, None))


if __name__ == "__main__":
    unittest.main()

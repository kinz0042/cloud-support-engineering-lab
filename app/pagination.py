"""Bounded keyset cursors for the synthetic order API; cursors are not secrets."""
import base64
import binascii
import json
import re
import uuid
from datetime import datetime
from urllib.parse import parse_qsl

MAX_QUERY = 512
MAX_CURSOR = 256
MAX_LIMIT = 100


def encode_cursor(row):
    payload = json.dumps({"t": row["created_at"], "id": row["id"]}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_cursor(token):
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", token):
        raise ValueError("invalid cursor")
    try:
        raw = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
        data = json.loads(raw)
        if not isinstance(data, dict) or set(data) != {"t", "id"}:
            raise ValueError("invalid cursor fields")
        if not isinstance(data["t"], str) or not isinstance(data["id"], str):
            raise ValueError("invalid cursor values")
        timestamp = datetime.fromisoformat(data["t"])
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("cursor timestamp requires a timezone")
        identifier = uuid.UUID(data["id"])
    except (ValueError, TypeError, UnicodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise ValueError("invalid cursor") from exc
    return timestamp, str(identifier)


def parse_page_query(query):
    if len(query) > MAX_QUERY:
        raise ValueError("query too long")
    try:
        pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True,
                          errors="strict", max_num_fields=2)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid query") from exc
    params = {}
    for key, value in pairs:
        if key not in ("limit", "cursor") or key in params:
            raise ValueError("unknown or duplicate parameter")
        params[key] = value
    raw_limit = params.get("limit", str(MAX_LIMIT))
    if not raw_limit.isascii() or not raw_limit.isdigit() or len(raw_limit) > 3:
        raise ValueError("invalid limit")
    limit = int(raw_limit)
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError("invalid limit")
    cursor = decode_cursor(params["cursor"]) if "cursor" in params else None
    return limit, cursor

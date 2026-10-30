"""Read all pages from the local synthetic RelayDesk API without printing credentials."""
import argparse
import http.client
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

BASE_URL = "http://127.0.0.1:8081/v1/orders"
KEYS = {"acme": "acme-local-key", "orbit": "orbit-local-key"}
MAX_PAGE_BODY = 256 * 1024


class PaginationError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def collect(base_url, token, limit=25, max_pages=1000):
    target = urlsplit(base_url)
    try:
        port = target.port
    except ValueError as exc:
        raise PaginationError("invalid local API URL") from exc
    if (target.scheme != "http" or target.hostname != "127.0.0.1" or port is None or
            target.username is not None or target.password is not None or target.path != "/v1/orders" or
            target.query or target.fragment):
        raise PaginationError("only the local synthetic order API is supported")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100 or max_pages < 1:
        raise PaginationError("invalid page bounds")
    opener = build_opener(ProxyHandler({}), NoRedirect())
    ids, cursors = set(), set()
    cursor = None
    for page_number in range(1, max_pages + 1):
        params = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        request = Request(base_url + "?" + urlencode(params), headers={"Authorization": "Bearer " + token})
        try:
            with opener.open(request, timeout=5) as response:
                declared = response.headers.get("Content-Length")
                if declared is not None:
                    if not declared.isascii() or not declared.isdigit():
                        raise PaginationError("API returned an invalid response length")
                    if len(declared) > 6 or int(declared) > MAX_PAGE_BODY:
                        raise PaginationError("API page exceeded the response limit")
                raw = response.read(MAX_PAGE_BODY + 1)
                if len(raw) > MAX_PAGE_BODY:
                    raise PaginationError("API page exceeded the response limit")
                if declared is not None and len(raw) != int(declared):
                    raise PaginationError("API returned an incomplete response")
                body = json.loads(raw)
        except HTTPError as exc:
            status = exc.code
            exc.close()
            raise PaginationError(f"API returned HTTP {status}") from None
        except (URLError, TimeoutError, OSError, http.client.HTTPException):
            raise PaginationError("local API is unavailable") from None
        except (ValueError, UnicodeError):
            raise PaginationError("API returned invalid JSON") from None
        if not isinstance(body, dict) or not isinstance(body.get("orders"), list) or "next_cursor" not in body:
            raise PaginationError("API returned an invalid page")
        if len(body["orders"]) > limit:
            raise PaginationError("API returned more orders than requested")
        for order in body["orders"]:
            identifier = order.get("id") if isinstance(order, dict) else None
            if not isinstance(identifier, str) or not identifier or identifier in ids:
                raise PaginationError("API returned a missing or duplicate order ID")
            ids.add(identifier)
        next_cursor = body["next_cursor"]
        if next_cursor is None:
            return {"pages": page_number, "orders": len(ids)}
        if (not body["orders"] or not isinstance(next_cursor, str) or
                not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", next_cursor) or next_cursor in cursors):
            raise PaginationError("API returned an invalid or repeated cursor")
        cursors.add(next_cursor)
        cursor = next_cursor
    raise PaginationError("maximum page count exceeded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", choices=sorted(KEYS), default="acme")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    try:
        result = collect(BASE_URL, KEYS[args.tenant], args.limit)
    except PaginationError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"tenant": args.tenant, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

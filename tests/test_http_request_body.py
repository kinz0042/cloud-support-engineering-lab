"""Exercise framing and stalled uploads over actual local TCP connections."""
import json
import socket
import threading
import unittest

from app.relay_api import make_server


class Store:
    def __init__(self):
        self.created = []
        self.callbacks = []

    def create_order(self, tenant, external_id):
        self.created.append((tenant, external_id))
        return {"id": "test", "external_id": external_id}, True

    def record_callback(self, event_id, order_id):
        self.callbacks.append((event_id, order_id))
        return True


class RequestBodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store()
        cls.server = make_server(0, cls.store, {"acme": "demo-key"}, "demo-secret")
        cls.server.body_read_idle_timeout = 0.2
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.store.created.clear()
        self.store.callbacks.clear()

    def send(self, raw, half_close=False):
        with socket.create_connection(("127.0.0.1", self.server.server_port), timeout=3) as conn:
            conn.sendall(raw)
            if half_close:
                conn.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        headers, body = b"".join(chunks).split(b"\r\n\r\n", 1)
        return int(headers.split(b" ", 2)[1]), json.loads(body)

    def test_stalled_order_and_callback_timeout_without_mutation(self):
        for path, auth in ((b"/v1/orders", b"Authorization: Bearer demo-key\r\n"),
                           (b"/v1/callbacks", b"")):
            with self.subTest(path=path):
                request = b"POST " + path + b" HTTP/1.1\r\nHost: localhost\r\n" + auth + b"Content-Length: 50\r\n\r\n{"
                with self.assertLogs("relaydesk", level="INFO") as logs:
                    status, body = self.send(request)
                self.assertEqual((status, body["error"]), (408, "request_timeout"))
                self.assertIn("body_read_timeout", " ".join(logs.output))
                self.assertNotIn("demo-key", " ".join(logs.output))
        self.assertEqual(self.store.created, [])
        self.assertEqual(self.store.callbacks, [])

    def test_incomplete_body_and_ambiguous_framing_rejected(self):
        prefix = b"POST /v1/orders HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer demo-key\r\n"
        for headers, body in ((b"Content-Length: 30\r\n", b"{}"),
                              (b"Content-Length: 2\r\nContent-Length: 2\r\n", b"{}"),
                              (b"Content-Length: 2\r\nTransfer-Encoding: chunked\r\n", b"{}"),
                              (b"Transfer-Encoding: chunked\r\n", b"0\r\n\r\n"),
                              (b"Content-Length: 99999\r\n", b"")):
            with self.subTest(headers=headers):
                status, response = self.send(prefix + headers + b"\r\n" + body, half_close=True)
                self.assertEqual((status, response["error"]), (400, "invalid_request"))
        self.assertEqual(self.store.created, [])

    def test_valid_json_still_creates_order(self):
        body = b'{"external_id":"normal"}'
        request = (b"POST /v1/orders HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer demo-key\r\n"
                   + b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body)
        status, response = self.send(request)
        self.assertEqual(status, 201)
        self.assertTrue(response["created"])
        self.assertEqual(self.store.created, [("acme", "normal")])


if __name__ == "__main__":
    unittest.main()

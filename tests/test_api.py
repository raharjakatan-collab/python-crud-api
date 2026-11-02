from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import json
import unittest

import app


class APITestCase(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.original_data_file = app.DATA_FILE
        app.DATA_FILE = Path(self.tmp_dir.name) / "messages.json"

        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), app.APIHandler
        )
        Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        app.DATA_FILE = self.original_data_file
        self.tmp_dir.cleanup()

    def request(self, method, path, body=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port)
        conn.request(method, path, body=body)
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        conn.close()
        return response.status, payload

    def post_message(self, message):
        return self.request(
            "POST", "/messages", json.dumps({"message": message})
        )

    def test_health_returns_active(self):
        status, payload = self.request("GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "active")

    def test_post_creates_message_with_timestamp(self):
        status, payload = self.post_message("Halo")

        self.assertEqual(status, 201)
        self.assertEqual(payload["message"]["message"], "Halo")
        self.assertIn("created_at", payload["message"])

    def test_post_rejects_empty_message(self):
        status, _ = self.post_message("   ")

        self.assertEqual(status, 400)

    def test_post_rejects_message_over_500_characters(self):
        status, _ = self.post_message("x" * 501)

        self.assertEqual(status, 400)

    def test_post_rejects_invalid_json(self):
        status, _ = self.request("POST", "/messages", "bukan json")

        self.assertEqual(status, 400)

    def test_post_rejects_json_that_is_not_an_object(self):
        status, _ = self.request("POST", "/messages", "[1, 2]")

        self.assertEqual(status, 400)

    def test_get_message_by_index(self):
        self.post_message("Pertama")
        self.post_message("Kedua")

        status, payload = self.request("GET", "/messages/1")

        self.assertEqual(status, 200)
        self.assertEqual(payload["index"], 1)
        self.assertEqual(payload["message"]["message"], "Kedua")

    def test_get_message_unknown_index_returns_404(self):
        status, _ = self.request("GET", "/messages/999")

        self.assertEqual(status, 404)

    def test_get_message_non_integer_index_returns_400(self):
        status, _ = self.request("GET", "/messages/abc")

        self.assertEqual(status, 400)

    def test_delete_removes_message(self):
        self.post_message("Hapus saya")

        status, _ = self.request("DELETE", "/messages?index=0")
        _, listing = self.request("GET", "/messages")

        self.assertEqual(status, 200)
        self.assertEqual(listing["total"], 0)

    def test_delete_unknown_index_returns_404(self):
        status, _ = self.request("DELETE", "/messages?index=999")

        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()

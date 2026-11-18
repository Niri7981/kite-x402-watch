"""Local challenge simulator. Edit the terms JSON while the server is running."""
import argparse
import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def handler(path):
    class Seller(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                option = json.loads(path.read_text())
            except (OSError, ValueError):
                self.send_error(503)
                return
            challenge = {"x402Version": 2, "accepts": [option], "resource": {
                "url": "http://127.0.0.1:%d/quote" % self.server.server_port,
                "description": "Example quote", "mimeType": "application/json"}}
            self.send_response(402)
            self.send_header("PAYMENT-REQUIRED", base64.b64encode(json.dumps(challenge).encode()).decode())
            self.end_headers()
    return Seller


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("terms", type=Path)
    parser.add_argument("--port", type=int, default=8408)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler(args.terms)) as server:
        server.serve_forever()

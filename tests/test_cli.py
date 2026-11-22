import base64
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from examples.seller import handler
from kite_watch.terms import decode, price

ROOT = Path(__file__).resolve().parents[1]


class Watch(unittest.TestCase):
    def test_http_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            terms_file = Path(tmp) / "terms"
            baseline = Path(tmp) / "baseline"
            terms = json.loads((ROOT / "examples/terms.json").read_text())
            terms_file.write_text(json.dumps(terms))
            with ThreadingHTTPServer(("127.0.0.1", 0), handler(terms_file)) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                def cli(*args):
                    result = subprocess.run([sys.executable, "-m", "kite_watch.cli", *args,
                        "--baseline", str(baseline), "--json"], capture_output=True, text=True, cwd=ROOT)
                    return result.returncode, json.loads(result.stdout)
                try:
                    url = f"http://127.0.0.1:{server.server_port}/quote"
                    self.assertEqual(cli("snapshot", url)[0], 0)
                    original = baseline.read_bytes()
                    self.assertEqual(cli("check"), (0, {"status": "unchanged", "url": url, "changes": {}}))
                    self.assertEqual(cli("snapshot", url)[0], 2)
                    for field, value in [("amount", "10000"), ("payTo", "0x" + "2"*40),
                                         ("network", "eip155:2368"), ("asset", "0x" + "3"*40)]:
                        with self.subTest(field=field):
                            terms_file.write_text(json.dumps({**terms, field: value}))
                            code, report = cli("check")
                            self.assertEqual(code, 1)
                            self.assertEqual(list(report["changes"]), [field])
                            self.assertEqual(report["changes"][field]["after"], value)
                    result = subprocess.run(
                        [sys.executable, "-m", "kite_watch.cli", "check", "--baseline", str(baseline)],
                        capture_output=True, text=True, cwd=ROOT, timeout=5,
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("price: 0.001 USDC.e -> 1000 atomic units", result.stdout)
                    terms_file.unlink()
                    self.assertEqual(cli("check"), (2, {"status": "error", "error": "expected HTTP 402, got HTTP 503"}))
                    self.assertEqual(baseline.read_bytes(), original)
                finally:
                    server.shutdown()
                    thread.join()
            self.assertEqual(cli("check")[0], 2)
            code, report = cli("inspect")
            self.assertEqual(code, 0)
            self.assertEqual(report, {"status": "inspected", "url": url,
                                      "terms": json.loads(original)["terms"], "price": "0.001 USDC.e"})
            self.assertEqual(baseline.read_bytes(), original)
            baseline.write_text(json.dumps({**json.loads(original), "version": True}))
            self.assertEqual(cli("inspect"), (2, {"status": "error", "error": "unsupported baseline format"}))

    def test_reports_timeout_for_seller_that_never_sends_headers(self):
        request_received = threading.Event()
        finish_request = threading.Event()

        class SlowSeller(BaseHTTPRequestHandler):
            def do_GET(self):
                request_received.set()
                finish_request.wait(timeout=5)

        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp) / "baseline.json"
            with ThreadingHTTPServer(("127.0.0.1", 0), SlowSeller) as server:
                url = f"http://127.0.0.1:{server.server_port}/quote"
                terms = json.loads((ROOT / "examples/terms.json").read_text())
                baseline.write_text(json.dumps({"version": 1, "url": url, "terms": terms}))
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "kite_watch.cli", "check", "--baseline", str(baseline),
                         "--timeout", "0.5", "--json"], capture_output=True, text=True, cwd=ROOT, timeout=5,
                    )
                    self.assertTrue(request_received.is_set())
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(json.loads(result.stdout), {"status": "error", "error": "endpoint request timed out"})
                finally:
                    finish_request.set()
                    server.shutdown()
                    thread.join()

    def test_reject_ambiguous_or_invalid_challenges(self):
        for options in ([], [{}, {}], [{"scheme":"exact","amount":1}]):
            header = base64.b64encode(json.dumps({"x402Version":2,"accepts":options}).encode())
            with self.assertRaises(ValueError):
                decode(header)
        with self.assertRaises(ValueError):
            decode("not-base64")

    def test_known_kite_prices_preserve_atomic_precision(self):
        cases = [
            ("eip155:2366", "0x7ab6f3ed87c42ef0adb67ed95090f8bf5240149e", "1000001", "1.000001 USDC.e"),
            ("eip155:2368", "0x38129cf4ce5e183eff248f42a7d345bb1b47621a", "1", "0.000000000000000001 pieUSD"),
            ("eip155:2368", "0x7ab6f3ed87c42ef0adb67ed95090f8bf5240149e", "1000001", "1000001 atomic units"),
        ]
        for network, asset, amount, expected in cases:
            with self.subTest(network=network, asset=asset):
                self.assertEqual(price({"network": network, "asset": asset, "amount": amount}), expected)

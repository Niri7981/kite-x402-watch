import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from examples.seller import handler
from kite_watch.terms import decode
import base64

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
                    self.assertEqual(cli("check")[0], 0)
                    self.assertEqual(cli("snapshot", url)[0], 2)
                    for field, value in [("amount", "10000"), ("payTo", "0x" + "2"*40),
                                         ("network", "eip155:2368"), ("asset", "0x" + "3"*40)]:
                        with self.subTest(field=field):
                            terms_file.write_text(json.dumps({**terms, field: value}))
                            code, report = cli("check")
                            self.assertEqual(code, 1)
                            self.assertEqual(list(report["changes"]), [field])
                            self.assertEqual(report["changes"][field]["after"], value)
                    terms_file.unlink()
                    self.assertEqual(cli("check")[0], 2)
                    self.assertEqual(baseline.read_bytes(), original)
                finally:
                    server.shutdown()
                    thread.join()
            self.assertEqual(cli("check")[0], 2)

    def test_reject_ambiguous_or_invalid_challenges(self):
        for options in ([], [{}, {}], [{"scheme":"exact","amount":1}]):
            header = base64.b64encode(json.dumps({"x402Version":2,"accepts":options}).encode())
            with self.assertRaises(ValueError):
                decode(header)
        with self.assertRaises(ValueError):
            decode("not-base64")

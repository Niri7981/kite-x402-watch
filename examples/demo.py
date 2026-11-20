"""Run the installed kite-watch command against a simulated local seller."""
import argparse
import json
import shutil
import subprocess
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from seller import handler


def invoke(cli, directory, expected_code, expected_status, *args):
    result = subprocess.run(
        [cli, *args, "--json"], cwd=directory, capture_output=True, text=True, timeout=15,
    )
    if result.returncode != expected_code:
        raise RuntimeError(f"{args[0]}: expected exit {expected_code}, got {result.returncode}: "
                           f"{result.stdout.strip()} {result.stderr.strip()}")
    report = json.loads(result.stdout)
    if report.get("status") != expected_status:
        raise RuntimeError(f"{args[0]}: expected {expected_status}, got {report}")
    print(f"{args[0]:8} exit {result.returncode}: {report['status']}", flush=True)
    return report


def demo(cli):
    terms = json.loads(Path(__file__).with_name("terms.json").read_text(encoding="utf8"))
    terms["amount"] = "1000000"
    with tempfile.TemporaryDirectory(prefix="kite-watch-demo-") as tmp:
        terms_file = Path(tmp) / "terms.json"
        baseline = Path(tmp) / "kite-baseline.json"
        terms_file.write_text(json.dumps(terms), encoding="utf8")
        with ThreadingHTTPServer(("127.0.0.1", 0), handler(terms_file)) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/quote"
                invoke(cli, tmp, 0, "saved", "snapshot", url)
                original = baseline.read_bytes()
                invoke(cli, tmp, 0, "unchanged", "check")

                terms_file.write_text(json.dumps({**terms, "amount": "2000000"}), encoding="utf8")
                changed = invoke(cli, tmp, 1, "changed", "check")
                if changed.get("changes") != {"amount": {"before": "1000000", "after": "2000000"}}:
                    raise RuntimeError(f"unexpected amount diff: {changed}")
                print("         1 -> 2 USDC.e (1000000 -> 2000000 atomic units)", flush=True)

                terms_file.unlink()
                error = invoke(cli, tmp, 2, "error", "check")
                if "503" not in error.get("error", ""):
                    raise RuntimeError(f"expected a seller-unavailable error: {error}")
                print(f"         {error['error']}", flush=True)
                saved = invoke(cli, tmp, 0, "inspected", "inspect")
                if saved.get("price") != "1 USDC.e":
                    raise RuntimeError(f"unexpected saved price: {saved}")
                if baseline.read_bytes() != original:
                    raise RuntimeError("checks modified the approved baseline")
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", default="kite-watch", help="installed kite-watch executable")
    args = parser.parse_args()
    executable = shutil.which(args.cli)
    if not executable:
        parser.error("kite-watch not found; install the package in the active environment first")
    demo(str(Path(executable).absolute()))

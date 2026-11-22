"""Command line interface. No credential or signing support."""
import argparse
import http.client
import json
import math
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

from .terms import FIELDS, decode, normalize, price


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def validate_url(url):
    if not isinstance(url, str):
        raise ValueError("invalid endpoint")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username is not None or parts.fragment:
        raise ValueError("expected an HTTP(S) URL without credentials or fragment")


def observe(url, timeout):
    validate_url(url)
    try:
        response = build_opener(NoRedirect).open(url, timeout=timeout)
    except HTTPError as exc:
        response = exc
    except TimeoutError as exc:
        raise ValueError("endpoint request timed out") from exc
    except URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise ValueError("endpoint request timed out") from exc
        raise ValueError(f"could not reach endpoint: {exc.reason}") from exc
    with response:
        if response.status != 402:
            raise ValueError(f"expected HTTP 402, got HTTP {response.status}")
        return decode(response.headers.get("payment-required"))


def positive_timeout(value):
    try:
        seconds = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("timeout must be a positive number of seconds") from None
    if not math.isfinite(seconds) or not 0 < seconds <= 60:
        raise argparse.ArgumentTypeError("timeout must be greater than 0 and at most 60 seconds")
    return seconds


def load_baseline(path):
    data = json.loads(path.read_text(encoding="utf8"))
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("unsupported baseline format")
    url = data.get("url")
    validate_url(url)
    return url, normalize(data.get("terms"))


def run(args):
    path = args.baseline
    if args.command == "snapshot":
        terms = observe(args.url, args.timeout)
        if terms["network"] not in {"eip155:2366", "eip155:2368"}:
            raise ValueError("initial baseline must advertise a Kite network")
        data = {"version": 1, "url": args.url, "terms": terms}
        with path.open("x", encoding="utf8") as out:
            json.dump(data, out, indent=2)
            out.write("\n")
        return 0, {"status": "saved", **data}, f"Saved {path}: {price(terms)}, payTo {terms['payTo']}"
    url, old = load_baseline(path)
    if args.command == "inspect":
        display_price = price(old)
        lines = ["Saved payment terms", f"url: {url}", *(f"{key}: {old[key]}" for key in FIELDS),
                 f"price: {display_price}"]
        return 0, {"status": "inspected", "url": url, "terms": old, "price": display_price}, "\n".join(lines)
    new = observe(url, args.timeout)
    changes = {k: {"before": old[k], "after": new[k]} for k in FIELDS if new[k] != old[k]}
    lines = [f"{k}: {v['before']} -> {v['after']}" for k, v in changes.items()]
    if changes.keys() & {"amount", "asset", "network"}:
        lines.append(f"price: {price(old)} -> {price(new)}")
    status = "changed" if changes else "unchanged"
    return int(bool(changes)), {"status": status, "url": url, "changes": changes}, "\n".join([status, *lines])


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kite-watch")
    subs = parser.add_subparsers(dest="command", required=True)
    snapshot = subs.add_parser("snapshot", help="create a new baseline for review")
    snapshot.add_argument("url")
    check = subs.add_parser("check", help="compare with a saved baseline")
    inspect = subs.add_parser("inspect", help="show saved payment terms without contacting the endpoint")
    for sub in (snapshot, check, inspect):
        sub.add_argument("--baseline", type=Path, default=Path("kite-baseline.json"))
        sub.add_argument("--json", action="store_true")
    for sub in (snapshot, check):
        sub.add_argument("--timeout", type=positive_timeout, default=5, metavar="SECONDS",
                         help="network timeout in seconds, up to 60 (default: 5)")
    args = parser.parse_args(argv)
    try:
        code, payload, message = run(args)
    except (OSError, ValueError, http.client.HTTPException, RecursionError) as exc:
        code, payload, message = 2, {"status": "error", "error": str(exc)}, f"error: {exc}"
    print(json.dumps(payload, ensure_ascii=False) if args.json else message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

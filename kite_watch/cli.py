"""Command line interface. No credential or signing support."""
import argparse
import http.client
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

from .terms import FIELDS, decode, normalize, price


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def observe(url):
    if not isinstance(url, str):
        raise ValueError("invalid endpoint")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username is not None or parts.fragment:
        raise ValueError("expected an HTTP(S) URL without credentials or fragment")
    try:
        response = build_opener(NoRedirect).open(url, timeout=5)
    except HTTPError as exc:
        response = exc
    with response:
        if response.status != 402:
            raise ValueError(f"expected HTTP 402, got {response.status}")
        return decode(response.headers.get("payment-required"))


def run(args):
    path = args.baseline
    if args.command == "snapshot":
        terms = observe(args.url)
        if terms["network"] not in {"eip155:2366", "eip155:2368"}:
            raise ValueError("initial baseline must advertise a Kite network")
        data = {"version": 1, "url": args.url, "terms": terms}
        with path.open("x", encoding="utf8") as out:
            json.dump(data, out, indent=2)
            out.write("\n")
        return 0, {"status": "saved", **data}, f"Saved {path}: {price(terms)}, payTo {terms['payTo']}"
    data = json.loads(path.read_text(encoding="utf8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("unsupported baseline format")
    old = normalize(data.get("terms"))
    new = observe(data.get("url"))
    changes = {k: {"before": old[k], "after": new[k]} for k in FIELDS if new[k] != old[k]}
    lines = [f"{k}: {v['before']} -> {v['after']}" for k, v in changes.items()]
    if "amount" in changes:
        lines.append(f"price: {price(old)} -> {price(new)}")
    status = "changed" if changes else "unchanged"
    return int(bool(changes)), {"status": status, "url": data["url"], "changes": changes}, "\n".join([status, *lines])


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kite-watch")
    subs = parser.add_subparsers(dest="command", required=True)
    snapshot = subs.add_parser("snapshot", help="create a new baseline for review")
    snapshot.add_argument("url")
    for sub in (snapshot, subs.add_parser("check", help="compare with a saved baseline")):
        sub.add_argument("--baseline", type=Path, default=Path("kite-baseline.json"))
        sub.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        code, payload, message = run(args)
    except (OSError, ValueError, http.client.HTTPException, RecursionError) as exc:
        code, payload, message = 2, {"status": "error", "error": str(exc)}, f"error: {exc}"
    print(json.dumps(payload, ensure_ascii=False) if args.json else message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

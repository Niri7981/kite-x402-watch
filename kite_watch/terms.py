"""Validate advertised terms and format known Kite assets without rounding."""
import base64
import json
import re

TOKENS = {
    ("eip155:2366", "0x7ab6f3ed87c42ef0adb67ed95090f8bf5240149e"): ("USDC.e", 6),
    ("eip155:2368", "0x38129cf4ce5e183eff248f42a7d345bb1b47621a"): ("pieUSD", 18),
}
FIELDS = ("network", "asset", "amount", "payTo")


def normalize(option):
    if not isinstance(option, dict):
        raise ValueError("expected payment option object")
    result = {key: option.get(key) for key in FIELDS}
    for key, pattern in (("network", r"eip155:[1-9][0-9]*"), ("asset", r"0x[0-9a-fA-F]{40}"),
                         ("payTo", r"0x[0-9a-fA-F]{40}"), ("amount", r"[0-9]{1,78}")):
        if not isinstance(result[key], str) or not re.fullmatch(pattern, result[key]):
            raise ValueError(f"invalid {key}")
    result["amount"] = str(int(result["amount"]))
    for key in ("asset", "payTo"):
        result[key] = result[key].lower()
    return result


def decode(header):
    if not header or len(header) > 65536:
        raise ValueError("missing or oversized PAYMENT-REQUIRED header")
    obj = json.loads(base64.b64decode(header, validate=True))
    if not isinstance(obj, dict) or type(obj.get("x402Version")) is not int or obj["x402Version"] != 2:
        raise ValueError("expected an x402 v2 challenge")
    options = obj.get("accepts")
    if not isinstance(options, list) or len(options) != 1 or not isinstance(options[0], dict) or options[0].get("scheme") != "exact":
        raise ValueError("v1 of kite-watch supports one exact payment option")
    return normalize(options[0])


def price(terms):
    token = TOKENS.get((terms["network"], terms["asset"]))
    if not token:
        return terms["amount"] + " atomic units"
    symbol, decimals = token
    digits = terms["amount"].zfill(decimals + 1)
    fraction = digits[-decimals:].rstrip("0")
    return digits[:-decimals] + ("." + fraction if fraction else "") + " " + symbol

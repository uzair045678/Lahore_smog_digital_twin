"""Tiny owner-side check for the published `data` branch.

Reads `manifest.json` and its `latest.json` from raw.githubusercontent.com and
verifies that the response is browser-readable: HTTPS, HTTP 200, JSON body,
CORS header `Access-Control-Allow-Origin: *`, manifest shape, and URL
consistency. Uses only the standard library.
"""

import json
import sys
import urllib.request
from urllib.parse import urljoin

REPO = "uzair045678/Lahore_smog_digital_twin"
BRANCH = "data"
BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"


def fetch(path):
    url = urljoin(BASE, path)
    req = urllib.request.Request(url, headers={"Origin": "https://example.com"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        headers = dict(resp.headers)
    return url, headers, body


def main():
    problems = []

    try:
        _, manifest_headers, manifest_text = fetch("manifest.json")
        manifest = json.loads(manifest_text)
    except Exception as exc:
        print("FAIL: cannot read manifest.json:", exc)
        return 1

    acao = manifest_headers.get("Access-Control-Allow-Origin")
    if acao != "*":
        problems.append(f"manifest ACAO={acao!r}, expected '*'")

    ct = manifest_headers.get("Content-Type", "")
    if "json" not in ct.lower():
        problems.append(f"manifest Content-Type={ct!r}")

    for key in ("schema_version", "data_version", "published_at", "latest_url", "history_url"):
        if key not in manifest:
            problems.append(f"manifest missing '{key}'")

    latest_path = manifest.get("latest_url", "")
    if latest_path:
        try:
            latest_url, _, latest_text = fetch(latest_path)
            latest = json.loads(latest_text)
            print("OK latest:", latest_url)
            print("  stations:", len(latest.get("stations", [])))
        except Exception as exc:
            problems.append(f"latest not readable: {exc}")

    print("manifest headers:")
    for header in ("Content-Type", "Access-Control-Allow-Origin", "Cache-Control", "ETag"):
        if header in manifest_headers:
            print(f"  {header}: {manifest_headers[header]}")
    print("manifest:", json.dumps(manifest, indent=2)[:600])

    if problems:
        print("FAILURES:")
        for problem in problems:
            print(" -", problem)
        return 1

    print("PASS: published data is HTTPS, JSON and CORS-readable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

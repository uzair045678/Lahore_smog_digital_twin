#!/usr/bin/env python
"""Download the reproducible OSM input used by the offline city normalizer.

This is intentionally not imported by the frontend or production build.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import urllib.request


DEFAULT_URL = "https://download.geofabrik.de/asia/pakistan-latest.osm.pbf"


def download(url: str, output: pathlib.Path) -> dict[str, str | int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "LahoreSmogTwin-city-pipeline/1.0"})
    with urllib.request.urlopen(request, timeout=900) as response, output.open("wb") as target:
        digest = hashlib.sha256()
        size = 0
        while chunk := response.read(1024 * 1024):
            target.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    return {"url": url, "path": str(output), "size_bytes": size, "sha256": digest.hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("data/raw/pakistan-latest.osm.pbf"))
    parser.add_argument("--metadata", type=pathlib.Path, default=pathlib.Path("city-data/source-manifest.json"))
    args = parser.parse_args()
    metadata = download(args.url, args.output)
    metadata.update({"provider": "Geofabrik", "license": "OpenStreetMap contributors, ODbL 1.0"})
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()

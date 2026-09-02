#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("--lock", type=Path, default=Path("local/models.lock.example"))
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    match = next((item for item in lock["models"] if item["filename"] == args.model.name), None)
    if match is None:
        raise SystemExit(f"FAIL no checksum entry for {args.model.name}")
    if args.model.stat().st_size != match["size_bytes"]:
        raise SystemExit("FAIL model size does not match the lock")
    actual = sha256(args.model)
    if actual != match["sha256"]:
        raise SystemExit("FAIL model SHA256 does not match the lock")
    print(f"PASS {args.model.name} {actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


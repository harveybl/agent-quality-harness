#!/usr/bin/env python3
"""Return the installed quality contract as native SessionStart context."""

from __future__ import annotations

import json
from pathlib import Path
import sys


def main() -> int:
    payload = json.load(sys.stdin)
    if payload.get("hook_event_name") != "SessionStart":
        raise ValueError("quality context only accepts SessionStart events")
    contract = Path(__file__).with_name("quality_contract.txt").read_text(encoding="utf-8")
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": contract,
                }
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

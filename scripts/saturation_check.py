"""Decide whether a sweep point can be skipped because the curve is saturated.

Usage: python scripts/saturation_check.py RESULTS_DIR FILE_PREFIX OFFERED_TPUT

Scans RESULTS_DIR for completed result files starting with FILE_PREFIX (e.g.
``tpcc_obol_gather_W100_`` or ``ycsbt_obol_K100000_``), parses the offered
throughput that follows the prefix in each filename, and counts how many
completed points below OFFERED_TPUT have p50 above the SLO. Once enough
points past the knee exist, running even higher rates adds nothing to the
saturation curve, so the caller can skip them.

Exit code 0 -> skip this point, 1 -> run it.

Tunables (environment):
    SATURATION_SLO_MS        p50 threshold in ms       (default 1000)
    SATURATION_EXTRA_POINTS  saturated points to keep  (default 4)
"""

import json
import os
import re
import sys


def main() -> int:
    results_dir, prefix, tput = sys.argv[1], sys.argv[2], int(sys.argv[3])
    slo_ms = float(os.getenv("SATURATION_SLO_MS", "1000"))
    extra_points = int(os.getenv("SATURATION_EXTRA_POINTS", "4"))

    if not os.path.isdir(results_dir):
        return 1

    saturated = 0
    for name in os.listdir(results_dir):
        if not name.startswith(prefix):
            continue
        m = re.match(r"(\d+)", name[len(prefix):])
        if not m or int(m.group(1)) >= tput:
            continue
        try:
            with open(os.path.join(results_dir, name), encoding="utf-8") as f:
                p50 = float(json.load(f)["latency (ms)"]["50"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
        if p50 > slo_ms:
            saturated += 1

    return 0 if saturated >= extra_points else 1


if __name__ == "__main__":
    sys.exit(main())

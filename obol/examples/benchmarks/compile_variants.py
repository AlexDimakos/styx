#!/usr/bin/env python3
"""Regenerate every compiled benchmark variant used by the experiment scripts.

For TPC-C this produces a *cumulative* optimization ladder: a naive baseline
with every optimization off, then one rung per optimization switched on, up to
the full system. Consecutive rungs differ by exactly one optimization, so
(rung N+1 - rung N) isolates that optimization's contribution.

    variant     source              compiler flags
    ---------   -----------------   ---------------------------------------
    naive       tpcc.py             OBOL_DISABLE_TAIL_CALL=1
                                    OBOL_CONTEXT_OVER_NETWORK=1
                                    OBOL_DISABLE_LIVENESS=1
    opt_tco     tpcc.py             OBOL_CONTEXT_OVER_NETWORK=1
                                    OBOL_DISABLE_LIVENESS=1
    opt_ctx     tpcc.py             OBOL_DISABLE_LIVENESS=1
    gather      tpcc.py             (none — the full system, top of the ladder)
    no_gather   tpcc_no_gather.py   (none — sequential source)

Every rung keeps `gather` on; `no_gather` sits outside the ladder and is the
source-level variant used by the main three-system comparison figure.

Each variant is written twice: once under ``compiled/`` (reference output,
next to the sources) and once into the TPC-C demo's ``functions`` package
where ``graph_compiled.py`` imports it from. YCSB has a single compiled
system, written to ``compiled/ycsb.py`` and ``demo/demo-ycsb/ycsb_compiled.py``.

Run from anywhere with the obol virtualenv:

    python obol/examples/benchmarks/compile_variants.py [--only tpcc|ycsb]
"""

import argparse
import os
from pathlib import Path

from obol.core import StyxTranspiler

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
ORIGINAL = HERE / "original"
COMPILED = HERE / "compiled"
TPCC_DEMO_FUNCTIONS = REPO_ROOT / "demo" / "demo-tpc-c" / "functions"
YCSB_DEMO = REPO_ROOT / "demo" / "demo-ycsb"

ABLATION_ENV_VARS = (
    "OBOL_DISABLE_TAIL_CALL",
    "OBOL_DISABLE_LIVENESS",
    "OBOL_CONTEXT_OVER_NETWORK",
)

# variant name -> (source file, {env var: value}).
# The first four entries are the cumulative ladder, in order: each one turns on
# exactly one more optimization than the entry above it.
TPCC_VARIANTS = {
    "naive": ("tpcc.py", {"OBOL_DISABLE_TAIL_CALL": "1",
                          "OBOL_CONTEXT_OVER_NETWORK": "1",
                          "OBOL_DISABLE_LIVENESS": "1"}),
    "opt_tco": ("tpcc.py", {"OBOL_CONTEXT_OVER_NETWORK": "1",
                            "OBOL_DISABLE_LIVENESS": "1"}),
    "opt_ctx": ("tpcc.py", {"OBOL_DISABLE_LIVENESS": "1"}),
    "gather": ("tpcc.py", {}),
    "no_gather": ("tpcc_no_gather.py", {}),
}


def compile_source(source: Path, env: dict[str, str]) -> str:
    """Compile one source file with the given ablation env vars set."""
    for var in ABLATION_ENV_VARS:
        os.environ.pop(var, None)
    os.environ.update(env)
    try:
        return StyxTranspiler(source.read_text(encoding="utf-8")).run()
    finally:
        for var in ABLATION_ENV_VARS:
            os.environ.pop(var, None)


def post_process(code: str) -> str:
    """Hoist `from __future__ import annotations` to the top of the module.

    The compiler emits its helper block above the user code, which pushes any
    __future__ import in the source below other statements — a SyntaxError on
    import. Move it to line 1.
    """
    lines = code.splitlines()
    future = "from __future__ import annotations"
    if future in (stripped := [ln.strip() for ln in lines]):
        lines.pop(stripped.index(future))
        lines.insert(0, future)
    return "\n".join(lines) + "\n"


def write(code: str, *targets: Path) -> None:
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code, encoding="utf-8")
        print(f"  wrote {target.relative_to(REPO_ROOT)}")


def compile_tpcc() -> None:
    for variant, (source_name, env) in TPCC_VARIANTS.items():
        print(f"[tpcc:{variant}] compiling {source_name} {env or ''}")
        code = post_process(compile_source(ORIGINAL / source_name, env))
        suffix = "" if variant == "gather" else f"_{variant}"
        write(
            code,
            COMPILED / f"tpcc{suffix}.py",
            TPCC_DEMO_FUNCTIONS / f"compiled_functions{suffix}.py",
        )


def compile_ycsb() -> None:
    print("[ycsb] compiling ycsb.py")
    code = post_process(compile_source(ORIGINAL / "ycsb.py", {}))
    write(code, COMPILED / "ycsb.py", YCSB_DEMO / "ycsb_compiled.py")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", choices=["tpcc", "ycsb"], default=None)
    args = parser.parse_args()

    if args.only in (None, "tpcc"):
        compile_tpcc()
    if args.only in (None, "ycsb"):
        compile_ycsb()


if __name__ == "__main__":
    main()

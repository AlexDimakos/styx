import os

N_PARTITIONS = 4

# ── Ablation switches ──────────────────────────────────────────────────
# Each optimization can be disabled through an environment variable so the
# benchmark tooling can emit ablation variants of the compiled output
# without editing compiler code. The flags are read at call time (not at
# import time) so a single process can compile several variants in a row.


def tail_call_enabled() -> bool:
    """Distributed tail-call optimization: when a step ends with
    `return other_entity.method(...)`, forward the caller's reply-to address
    instead of routing the response back through the intermediate entity."""
    return os.getenv("OBOL_DISABLE_TAIL_CALL", "0") != "1"


def liveness_enabled() -> bool:
    """Live-variable minimization of the serialized continuation context.
    Disabled, every variable defined so far is captured at each split."""
    return os.getenv("OBOL_DISABLE_LIVENESS", "0") != "1"


def context_in_state_enabled() -> bool:
    """Store continuation context in the operator's persistent function-context
    store and ship only a small integer id inside the reply_to record.
    Disabled, the full context dict travels through the network inside the
    reply_to stack on every hop (forward and backward)."""
    return os.getenv("OBOL_CONTEXT_OVER_NETWORK", "0") != "1"

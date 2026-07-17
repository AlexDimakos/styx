import importlib
import os

from styx.common.local_state_backends import LocalStateBackend
from styx.common.stateflow_graph import StateflowGraph

# Select which Obol-compiled TPC-C variant to run via env var so the batch
# orchestrator can switch systems without editing this file. 
#
#   TPCC_COMPILED_VARIANT=gather     -> full system (default)
#   TPCC_COMPILED_VARIANT=no_gather  -> sequential dispatch instead of gather fan-out
#   TPCC_COMPILED_VARIANT=no_tco     -> no distributed tail-call optimization
#   TPCC_COMPILED_VARIANT=ctx_net    -> live context shipped in reply_to over the network
#   TPCC_COMPILED_VARIANT=no_live    -> full defined-variable capture (no liveness analysis)
VARIANT_MODULES = {
    "gather": "functions.compiled_functions",
    "no_gather": "functions.compiled_functions_no_gather",
    "no_tco": "functions.compiled_functions_no_tco",
    "ctx_net": "functions.compiled_functions_ctx_net",
    "no_live": "functions.compiled_functions_no_live",
}

_variant = os.environ.get("TPCC_COMPILED_VARIANT", "gather")
if _variant not in VARIANT_MODULES:
    msg = f"Unknown TPCC_COMPILED_VARIANT '{_variant}'; expected one of {sorted(VARIANT_MODULES)}"
    raise ValueError(msg)
_module = importlib.import_module(VARIANT_MODULES[_variant])

warehouse_operator = _module.warehouse_operator
district_operator = _module.district_operator
item_operator = _module.item_operator
customer_operator = _module.customer_operator
customer_idx_operator = _module.customerindex_operator
stock_operator = _module.stock_operator
history_operator = _module.history_operator
order_operator = _module.order_operator
new_order_operator = _module.neworder_operator
order_line_operator = _module.orderline_operator
new_order_txn_operator = _module.newordertxn_operator
payment_txn_operator = _module.paymenttxn_operator

g = StateflowGraph("tpcc_benchmark", operator_state_backend=LocalStateBackend.DICT)
g.add_operators(
    customer_operator, district_operator, history_operator, item_operator,
    new_order_operator, order_operator, order_line_operator, stock_operator,
    warehouse_operator, new_order_txn_operator, customer_idx_operator,
    payment_txn_operator,
)

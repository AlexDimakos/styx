import os

# Select gather vs no-gather compiled functions via env var so the batch
# orchestrator can switch systems without editing this file.
#   TPCC_COMPILED_VARIANT=gather     -> functions.compiled_functions (default)
#   TPCC_COMPILED_VARIANT=no_gather  -> functions.compiled_functions_no_gather
if os.environ.get("TPCC_COMPILED_VARIANT", "gather") == "no_gather":
    from functions.compiled_functions_no_gather import (
        warehouse_operator,
        district_operator,
        item_operator,
        customer_operator,
        customerindex_operator as customer_idx_operator,
        stock_operator,
        history_operator,
        order_operator,
        neworder_operator as new_order_operator,
        orderline_operator as order_line_operator,
        newordertxn_operator as new_order_txn_operator,
        paymenttxn_operator as payment_txn_operator,
    )
else:
    from functions.compiled_functions import (
        warehouse_operator,
        district_operator,
        item_operator,
        customer_operator,
        customerindex_operator as customer_idx_operator,
        stock_operator,
        history_operator,
        order_operator,
        neworder_operator as new_order_operator,
        orderline_operator as order_line_operator,
        newordertxn_operator as new_order_txn_operator,
        paymenttxn_operator as payment_txn_operator,
    )
from styx.common.local_state_backends import LocalStateBackend
from styx.common.stateflow_graph import StateflowGraph

g = StateflowGraph("tpcc_benchmark", operator_state_backend=LocalStateBackend.DICT)
g.add_operators(
    customer_operator, district_operator, history_operator, item_operator,
    new_order_operator, order_operator, order_line_operator, stock_operator,
    warehouse_operator, new_order_txn_operator, customer_idx_operator,
    payment_txn_operator,
)

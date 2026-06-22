"""Shared Auth reporting helper import surface.

This module gives inspect-auth a neutral dependency for helper functions that are
currently implemented by ``verify_auth_flow.py`` for backwards compatibility.
Keeping this import surface separate from the inspect entrypoint makes the shared
contract explicit and provides the target module for a future physical helper
extraction without changing inspect-auth imports again.
"""

from __future__ import annotations

# readback helpers, and output helpers out of verify_auth_flow.py once this reporting
# surface stabilizes. For now this module is a neutral import shim so inspect-auth no
# longer depends directly on the verify-auth entrypoint.
from auth.verify_auth_flow import (  # noqa: F401
    AUTH_OUTPUT_PATH_ATTR,
    CHECK_AFFILIATION,
    CHECK_CONTACT,
    CHECK_ENTITY,
    CHECK_INVITE,
    NO_CACHE,
    AuthBatchResult,
    ConsoleLimit,
    blank_to_none,
    build_candidate_queries,
    build_inspection_identifier_rows,
    build_inspection_rows,
    build_inspection_summary,
    calculate_batch_count,
    dispose_engine,
    filter_inspection_states,
    flow,
    format_console_limit,
    get_candidate_count,
    get_candidate_page,
    is_csv_like_output_root,
    parse_auth_selection_mode,
    parse_console_limit,
    parse_inspect_filter,
    parse_manual_account_ids,
    parse_positive_int_tuple,
    print_inspection_identifier_rows,
    print_inspection_rows,
    print_inspection_summary,
    read_expected_accounts_for_candidates,
    resolve_task_result,
    run_auth_batch,
    task,
    write_inspection_report,
    write_inspection_summary_txt,
)

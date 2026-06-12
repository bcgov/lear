from enum import Enum
from typing import Any, List, Mapping, Optional, Sequence
from sqlalchemy import Engine, text
import logging
import re
import time


_SQL_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_UPDATE_STATUS_RESERVED_IDENTIFIERS = {
    'status',
    'error',
    'corp_num',
    'flow_run_id',
    'environment',
    'flow_name',
    'processed_status',
    'last_modified',
    'last_error',
}


def _validate_sql_identifier(identifier: str, *, context: str) -> None:
    """Validate an interpolated SQL identifier."""
    if not _SQL_IDENTIFIER_RE.match(str(identifier or '')):
        raise ValueError(f'Unsafe SQL identifier for {context}: {identifier}')


class ProcessingStatuses(str, Enum):
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

    # Used in corp_processing only
    PARTIAL = 'PARTIAL'


class ExtractTrackingService:
    """Provides services to update tracking tables in Colin extract DB.

    Currently it's used for corp_processing and colin_tracking tables.
    """

    def __init__(
        self,
        environment: str,
        db_engine: Engine,
        flow_name: str,
        table_name: str = 'corp_processing',
        *,
        statement_timeout_ms: Optional[int] = None
    ):
        _validate_sql_identifier(table_name, context='ExtractTrackingService.table_name')
        self.data_load_env = environment
        self.db_engine = db_engine
        self.flow_name = flow_name
        self.table_name = table_name
        self.statement_timeout_ms = statement_timeout_ms
        self.logger = logging.getLogger(__name__)

    def reserve_for_flow(self, base_query: str, flow_run_id: str,
                    extra_insert_cols: Optional[List[str]] = None,
                    *,
                    fallback_account_ids: Optional[str] = None,
                    base_query_params: Optional[Mapping[str, Any]] = None,
                    static_insert_values: Optional[Mapping[str, Any]] = None,
                    conflict_columns: Optional[Sequence[str]] = None) -> int:
        """Reserve corporations for processing in a specific flow run.

        Args:
            base_query: SQL query that selects corps to be processed
            flow_run_id: Unique identifier for this flow run
            fallback_account_ids: Optional CSV string of account IDs to use when candidate_corps does not
                                  provide account_ids.
            base_query_params: Optional bind parameters required by base_query.
            static_insert_values: Optional static column values to insert for every reserved row.
                                  Auth flows use this for operation identity columns.
            conflict_columns: Optional ON CONFLICT column list. Defaults to the legacy
                              (corp_num, flow_name, environment) conflict key used by non-auth callers.

        Returns:
            Number of corporations successfully reserved for this flow
        """
        # Columns from candidate_corps we also want to persist (e.g., 'account_ids')
        extra_cols: List[str] = extra_insert_cols or []
        static_values = dict(static_insert_values or {})
        base_params = dict(base_query_params or {})
        conflict_cols = list(conflict_columns or ('corp_num', 'flow_name', 'environment'))
        if not conflict_cols:
            raise ValueError('conflict_columns must contain at least one column')

        for col in [*extra_cols, *static_values.keys(), *conflict_cols]:
            _validate_sql_identifier(col, context='reserve_for_flow')
        for param_name in base_params.keys():
            _validate_sql_identifier(param_name, context='reserve_for_flow.base_query_params')
        reserved_param_names = {
            'flow_name',
            'status',
            'environment',
            'flow_run_id',
            'fallback_account_ids',
            *(f'static_{col}' for col in static_values.keys()),
        }
        conflicting_base_params = set(base_params).intersection(reserved_param_names)
        if conflicting_base_params:
            raise ValueError(
                f'base_query_params conflicts with reserve_for_flow parameters: '
                f'{sorted(conflicting_base_params)}'
            )

        base_insert_cols = {
            'corp_num',
            'corp_type_cd',
            'mig_batch_id',
            'flow_name',
            'processed_status',
            'environment',
            'flow_run_id',
            'create_date',
            'last_modified',
            'claimed_at',
        }
        duplicate_static_cols = base_insert_cols.intersection(static_values.keys())
        if duplicate_static_cols:
            raise ValueError(
                f'static_insert_values cannot override reserved tracking columns: {sorted(duplicate_static_cols)}'
            )
        # We may need to ensure 'account_ids' is present even when the base query doesn't return it
        include_account_ids = ('account_ids' in extra_cols) or (fallback_account_ids is not None)

        # Any pass-through extra columns EXCEPT 'account_ids' (handled specially)
        passthrough_cols = [c for c in extra_cols if c != 'account_ids']

        # Build the SELECT extras for available_corps
        select_extras_parts: List[str] = []
        if passthrough_cols:
            select_extras_parts.append(', ' + ', '.join(f"candidate_corps.{c}" for c in passthrough_cols))

        # Track whether the SQL will reference the :fallback_account_ids bind
        uses_fallback_bind = False
        if include_account_ids:
            if 'account_ids' in extra_cols:
                if fallback_account_ids is not None:
                    # base query yields account_ids; prefer it, but allow fallback when NULL
                    select_extras_parts.append(
                        ", COALESCE(candidate_corps.account_ids, CAST(:fallback_account_ids AS text)) AS account_ids"
                    )
                    uses_fallback_bind = True
                else:
                    # base query yields account_ids; no fallback
                    select_extras_parts.append(", candidate_corps.account_ids AS account_ids")
            else:
                # base query does NOT yield account_ids; inject constant fallback
                select_extras_parts.append(", CAST(:fallback_account_ids AS text) AS account_ids")
                uses_fallback_bind = True

        available_select_extras = ''.join(select_extras_parts)

        # Build the INSERT column list for extra values (passthrough and optionally account_ids)
        insert_extra_cols = list(passthrough_cols)
        if include_account_ids and 'account_ids' not in insert_extra_cols:
            insert_extra_cols.append('account_ids')

        duplicate_extra_static_cols = set(insert_extra_cols).intersection(static_values.keys())
        if duplicate_extra_static_cols:
            raise ValueError(
                f'static_insert_values duplicates candidate insert columns: {sorted(duplicate_extra_static_cols)}'
            )

        insert_identity_cols = list(static_values.keys())
        insert_optional_cols = insert_extra_cols + insert_identity_cols

        # These must include a leading comma when used in the SELECT list
        insert_extra_cols_csv = (', ' + ', '.join(insert_extra_cols)) if insert_extra_cols else ''
        insert_identity_cols_csv = ''.join(
            f', :static_{col} AS {col}' for col in insert_identity_cols
        )

        insert_optional_cols_sql = (
            ', '.join(insert_optional_cols) + ',' if insert_optional_cols else ''
        )
        conflict_cols_sql = ', '.join(conflict_cols)

        init_query = f"""
        WITH candidate_corps AS ({base_query}),
        available_corps AS (
            SELECT corp_num, corp_type_cd, mig_batch_id{available_select_extras}
            FROM candidate_corps
            FOR UPDATE SKIP LOCKED
        )
        INSERT INTO {self.table_name} (
            corp_num,
            corp_type_cd,
            mig_batch_id,
            {insert_optional_cols_sql}
            flow_name,
            processed_status,
            environment,
            flow_run_id,
            create_date,
            last_modified,
            claimed_at
        )
        SELECT 
            corp_num,
            corp_type_cd,
            mig_batch_id{insert_extra_cols_csv}{insert_identity_cols_csv},
            :flow_name,
            :status,
            :environment,
            :flow_run_id,
            NOW(),
            NOW(),
            NULL
        FROM available_corps
        ON CONFLICT ({conflict_cols_sql}) 
        DO NOTHING
        RETURNING corp_num
        """

        with self.db_engine.connect() as conn:
            with conn.begin():
                if self.statement_timeout_ms:
                    conn.execute(
                        text("SET LOCAL statement_timeout = :ms"),
                        {'ms': int(self.statement_timeout_ms)}
                    )

                params = {
                    'flow_name': self.flow_name,
                    'status': ProcessingStatuses.PENDING,
                    'environment': self.data_load_env,
                    'flow_run_id': flow_run_id
                }
                for col, value in static_values.items():
                    params[f'static_{col}'] = value.value if hasattr(value, 'value') else value
                # Only add the fallback bind if the SQL references it
                if uses_fallback_bind:
                    params['fallback_account_ids'] = fallback_account_ids

                params.update(base_params)

                start = time.monotonic()
                result = conn.execute(text(init_query), params)
                rows = result.fetchall()
                count = len(rows)
                elapsed = time.monotonic() - start

                self.logger.info(
                    "Initialized %s corps for flow run %s in %.2fs (include_account_ids=%s, fallback_account_ids=%s)",
                    count,
                    flow_run_id,
                    elapsed,
                    include_account_ids,
                    bool(fallback_account_ids)
                )
                return count

    def claim_batch(self, flow_run_id: str, batch_size: int,
                    extra_return_cols: Optional[List[str]] = None, as_dict: bool = False) -> List[str] | List[dict]:
        """Claim a batch of corporations for immediate processing within a flow run.

        Args:
            flow_run_id: Unique identifier for this flow run
            batch_size: Maximum number of corps to claim

        Returns:
            List of corporation numbers that were successfully claimed for processing
        """
        extra_cols = extra_return_cols or []
        for col in extra_cols:
            _validate_sql_identifier(col, context='claim_batch.extra_return_cols')
        ret_cols = ['tbl.corp_num', 'tbl.claimed_at'] + [f'tbl.{c}' for c in extra_cols]
        returning_sql = ', '.join(ret_cols)

        query = f"""
        WITH claimable AS (
            SELECT corp_num, id
            FROM {self.table_name}
            WHERE processed_status = :pending_status
            AND environment = :environment
            AND flow_name = :flow_name
            AND flow_run_id = :flow_run_id
            AND claimed_at IS NULL
            LIMIT :batch_size
            FOR UPDATE SKIP LOCKED
        )
        UPDATE {self.table_name} tbl
        SET processed_status = :processing_status,
            claimed_at = NOW(),
            last_modified = NOW()
        FROM claimable
        WHERE tbl.corp_num = claimable.corp_num
        AND  tbl.id = claimable.id
        RETURNING {returning_sql}
        """

        with self.db_engine.connect() as conn:
            with conn.begin():
                result = conn.execute(
                    text(query),
                    {
                        'pending_status': ProcessingStatuses.PENDING,
                        'processing_status': ProcessingStatuses.PROCESSING,
                        'environment': self.data_load_env,
                        'flow_name': self.flow_name,
                        'flow_run_id': flow_run_id,
                        'batch_size': batch_size
                    }
                )
                rows = result.fetchall()
                if extra_cols or as_dict:
                    keys = ['corp_num', 'claimed_at']  + extra_cols
                    claimed = [dict(zip(keys, row)) for row in rows]
                    if claimed:
                        self.logger.info(f"Claimed {len(claimed)} corps for flow {flow_run_id}")
                        self.logger.info(f"Corps: {', '.join([c['corp_num'] for c in claimed[:5]])}...")
                        for c in claimed:
                                self.logger.debug(f"  {c['corp_num']} claimed at {c['claimed_at']}")
                    return claimed
                else:
                    claimed_corps = [row[0] for row in rows]
                    if claimed_corps:
                        self.logger.info(f"Claimed {len(claimed_corps)} corps for flow {flow_run_id}")
                        self.logger.info(f"Corps: {', '.join(claimed_corps[:5])}...")
                        for corp, claimed_at in rows:
                            self.logger.debug(f"  {corp} claimed at {claimed_at}")
                    return claimed_corps

    def update_corp_status(
        self,
        flow_run_id: str,
        corp_num: str,
        status: ProcessingStatuses,
        error: str = None,
        **extra_params
    ) -> bool:
        """Update status for a corp."""
        for key in extra_params.keys():
            _validate_sql_identifier(key, context='update_corp_status')
            if key in _UPDATE_STATUS_RESERVED_IDENTIFIERS:
                raise ValueError(f'extra_params cannot override update_corp_status column/bind: {key}')

        set_clauses = [
            'processed_status = :status',
            'last_modified = NOW()',
            'last_error = CASE WHEN :error IS NOT NULL THEN :error ELSE last_error END',
        ]
        params = {
            'status': status,
            'error': error,
            'corp_num': corp_num,
            'flow_run_id': flow_run_id,
            'environment': self.data_load_env,
            'flow_name': self.flow_name
        }

        if self.table_name == 'colin_tracking':
            set_clauses.append('frozen = :frozen')
            set_clauses.append('in_early_adopter = :in_early_adopter')
            params['frozen'] = extra_params['frozen']
            params['in_early_adopter'] = extra_params['in_early_adopter']

        for k, v in extra_params.items():
            if k not in ('frozen', 'in_early_adopter'):
                set_clauses.append(f'{k} = :{k}')
                params[k] = v

        query = f"""
        UPDATE {self.table_name}
        SET {', '.join(set_clauses)}
        WHERE corp_num = :corp_num
        AND flow_run_id = :flow_run_id
        AND environment = :environment
        AND flow_name = :flow_name
        RETURNING corp_num
        """

        with self.db_engine.connect() as conn:
            with conn.begin():
                result = conn.execute(
                    text(query),
                    params
                )
                success = result.rowcount > 0
                if not success:
                    self.logger.warning(
                        f"Failed to update {corp_num} to {status} "
                        f"(flow_run_id={flow_run_id})"
                    )
                return success

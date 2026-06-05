from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from sqlalchemy import Engine, bindparam, text

from .auth_flow_utils import AUTH_DELETE_FLOW_NAME, auth_component_operation_logging_enabled


def _enum_value(value: Any) -> Any:
    """Return enum.value when present, otherwise the original value."""
    return value.value if hasattr(value, 'value') else value


def _truncate(value: Any, max_len: int) -> Optional[str]:
    """Normalize optional strings to fit auth tracking columns."""
    if value is None:
        return None
    text_value = str(value)
    if len(text_value) <= max_len:
        return text_value
    return text_value[: max_len - 3] + '...'


@dataclass(frozen=True)
class AuthDeleteTrackingCleanupSummary:
    """Compact summary of auth-delete-flow tracking rows selected for cleanup."""
    environment: str
    flow_name: str
    total_auth_processing_rows: int
    distinct_corp_count: int
    corp_sample: list[str]
    status_counts: dict[str, int]
    estimated_component_operation_rows: int


@dataclass(frozen=True)
class AuthComponentOperationRecord:
    """One auth_component_operation row.

    Values must be safe for persistence: no passcodes, bearer tokens, or raw unsafe payloads.
    """
    auth_processing_id: int
    corp_num: str
    flow_name: str
    flow_run_id: Any
    operation: Any
    operation_scope: Any
    component: Any
    dry_run: bool = False
    environment: Optional[str] = None
    target_type: Optional[str] = None
    target_value: Optional[str] = None
    action: Optional[str] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    detail: Optional[str] = None

    def as_insert_values(self, default_environment: str) -> dict:
        """Return normalized bind values for insertion."""
        return {
            'auth_processing_id': self.auth_processing_id,
            'corp_num': self.corp_num,
            'flow_name': self.flow_name,
            'environment': self.environment or default_environment,
            'flow_run_id': self.flow_run_id,
            'operation': _truncate(_enum_value(self.operation), 25),
            'operation_scope': _truncate(_enum_value(self.operation_scope), 25),
            'component': _truncate(_enum_value(self.component), 25),
            'target_type': _truncate(self.target_type, 50),
            'target_value': _truncate(self.target_value, 500),
            'action': _truncate(self.action, 50),
            'status_code': self.status_code,
            'error': _truncate(self.error, 1000),
            'detail': _truncate(self.detail, 2000),
            'dry_run': bool(self.dry_run),
        }


class AuthTrackingService:
    """Auth tracking helpers for component logs and tracking cleanup."""

    def __init__(
        self,
        environment: str,
        db_engine: Engine,
        *,
        log_component_operations: bool = False,
    ):
        self.environment = environment
        self.db_engine = db_engine
        self.log_component_operations = bool(log_component_operations)
        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_config(cls, config, db_engine: Engine) -> 'AuthTrackingService':
        """Build a service using config defaults.

        AUTH_LOG_COMPONENT_OPERATIONS defaults to false via auth_component_operation_logging_enabled().
        """
        return cls(
            getattr(config, 'DATA_LOAD_ENV', ''),
            db_engine,
            log_component_operations=auth_component_operation_logging_enabled(config),
        )

    @property
    def component_logging_enabled(self) -> bool:
        """Whether callers should build and insert component-operation rows."""
        return self.log_component_operations

    def build_component_operation(
        self,
        *,
        auth_processing_id: int,
        corp_num: str,
        flow_name: str,
        flow_run_id,
        operation,
        operation_scope,
        component,
        dry_run: bool = False,
        target_type: Optional[str] = None,
        target_value: Optional[str] = None,
        action: Optional[str] = None,
        status_code: Optional[int] = None,
        error: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> Optional[AuthComponentOperationRecord]:
        """Build a component-operation record, or None when logging is disabled.

        Future task integrations can call this helper to avoid constructing row payloads when
        AUTH_LOG_COMPONENT_OPERATIONS is false.
        """
        if not self.log_component_operations:
            return None
        return AuthComponentOperationRecord(
            auth_processing_id=auth_processing_id,
            corp_num=corp_num,
            flow_name=flow_name,
            environment=self.environment,
            flow_run_id=flow_run_id,
            operation=operation,
            operation_scope=operation_scope,
            component=component,
            target_type=target_type,
            target_value=target_value,
            action=action,
            status_code=status_code,
            error=error,
            detail=detail,
            dry_run=dry_run,
        )

    def insert_component_operations(
        self,
        records: Sequence[AuthComponentOperationRecord | Mapping[str, Any]],
    ) -> int:
        """Bulk insert component-operation rows in one transaction per batch.

        When component logging is disabled this intentionally performs no DB work.
        """
        if not self.log_component_operations or not records:
            return 0

        rows = [self._normalize_component_record(record) for record in records if record]
        if not rows:
            return 0

        return self._insert_component_operation_rows(rows)

    def insert_component_operations_required(
        self,
        records: Sequence[AuthComponentOperationRecord | Mapping[str, Any]],
    ) -> int:
        """Insert component-operation rows, reconciling affected auth rows on failure.

        Logging disabled or empty records remain a no-op. When logging is enabled,
        normalization/insert failures mark affected auth_processing rows FAILED where
        auth_processing_id can be recovered, then re-raise the original exception.
        """
        if not self.log_component_operations or not records:
            return 0

        rows = None
        try:
            rows = [self._normalize_component_record(record) for record in records if record]
            if not rows:
                return 0
            return self._insert_component_operation_rows(rows)
        except Exception as err:
            affected_records = rows if rows is not None else records
            auth_processing_ids = self._extract_auth_processing_ids(affected_records)
            if auth_processing_ids:
                try:
                    marked = self._mark_component_log_insert_failed(auth_processing_ids, err)
                    self.logger.error(
                        'Marked %s auth_processing rows FAILED after component-operation insert failure',
                        marked,
                    )
                except Exception:
                    self.logger.exception(
                        'Failed to reconcile auth_processing rows after component-operation insert failure'
                    )
            else:
                self.logger.error(
                    'Component-operation insert failed and no auth_processing_id values were available for reconciliation'
                )
            raise

    def _insert_component_operation_rows(self, rows: Sequence[Mapping[str, Any]]) -> int:
        query = """
        INSERT INTO auth_component_operation (
            auth_processing_id,
            corp_num,
            flow_name,
            environment,
            flow_run_id,
            operation,
            operation_scope,
            component,
            target_type,
            target_value,
            action,
            status_code,
            error,
            detail,
            dry_run,
            create_date
        ) VALUES (
            :auth_processing_id,
            :corp_num,
            :flow_name,
            :environment,
            :flow_run_id,
            :operation,
            :operation_scope,
            :component,
            :target_type,
            :target_value,
            :action,
            :status_code,
            :error,
            :detail,
            :dry_run,
            NOW()
        )
        """

        with self.db_engine.connect() as conn:
            with conn.begin():
                result = conn.execute(text(query), list(rows))
                inserted = result.rowcount if result.rowcount and result.rowcount > 0 else len(rows)

        self.logger.info('Inserted %s auth component operation rows', inserted)
        return inserted

    def _extract_auth_processing_ids(
        self,
        records: Sequence[AuthComponentOperationRecord | Mapping[str, Any]],
    ) -> list[int]:
        ids: list[int] = []
        seen = set()
        for record in records or []:
            if not record:
                continue
            value = (
                record.auth_processing_id
                if isinstance(record, AuthComponentOperationRecord)
                else record.get('auth_processing_id')
            )
            try:
                auth_processing_id = int(value)
            except Exception:
                continue
            if auth_processing_id not in seen:
                seen.add(auth_processing_id)
                ids.append(auth_processing_id)
        return ids

    def _mark_component_log_insert_failed(self, auth_processing_ids: Sequence[int], error: Exception) -> int:
        safe_error = _truncate(f'component_log_insert_error:{type(error).__name__}', 1000)
        safe_detail = _truncate('component_log_insert_error', 2000)
        query = text("""
        UPDATE auth_processing
        SET processed_status = 'FAILED',
            last_modified = NOW(),
            last_error = LEFT(
                CASE
                    WHEN last_error IS NULL OR last_error = '' THEN :error
                    ELSE last_error || '; ' || :error
                END,
                1000
            ),
            action_detail = LEFT(
                CASE
                    WHEN action_detail IS NULL OR action_detail = '' THEN :detail
                    ELSE action_detail || '; ' || :detail
                END,
                2000
            )
        WHERE id IN :auth_processing_ids
        """).bindparams(bindparam('auth_processing_ids', expanding=True))

        with self.db_engine.connect() as conn:
            with conn.begin():
                result = conn.execute(
                    query,
                    {
                        'auth_processing_ids': list(auth_processing_ids),
                        'error': safe_error,
                        'detail': safe_detail,
                    },
                )
                return result.rowcount or 0

    def _auth_delete_cleanup_target_cte(self, selected_corp_nums_sql: str) -> str:
        """Return shared target CTE for auth-delete-flow tracking cleanup."""
        return f"""
        WITH selected_corps AS (
            {selected_corp_nums_sql}
        ),
        target_auth_processing AS (
            SELECT ap.id, ap.corp_num, ap.processed_status
            FROM auth_processing ap
            JOIN selected_corps sc ON sc.corp_num = ap.corp_num
            WHERE ap.flow_name = :flow_name
              AND ap.environment = :environment
        )
        """

    def preview_delete_tracking_cleanup(
        self,
        selected_corp_nums_sql: str,
        *,
        flow_name: str = AUTH_DELETE_FLOW_NAME,
        sample_size: int = 10,
    ) -> AuthDeleteTrackingCleanupSummary:
        """Summarize auth-delete-flow tracking rows that would be deleted."""
        target_cte = self._auth_delete_cleanup_target_cte(selected_corp_nums_sql)
        params = {
            'environment': self.environment,
            'flow_name': flow_name,
            'sample_size': int(sample_size),
        }
        totals_sql = text(target_cte + """
        SELECT count(*) AS total_rows,
               count(DISTINCT corp_num) AS distinct_corp_count
        FROM target_auth_processing
        """)
        statuses_sql = text(target_cte + """
        SELECT COALESCE(processed_status, 'NULL') AS processed_status,
               count(*) AS row_count
        FROM target_auth_processing
        GROUP BY COALESCE(processed_status, 'NULL')
        ORDER BY processed_status
        """)
        component_count_sql = text(target_cte + """
        SELECT count(*)
        FROM auth_component_operation aco
        JOIN target_auth_processing target ON target.id = aco.auth_processing_id
        """)
        sample_sql = text(target_cte + """
        SELECT DISTINCT corp_num
        FROM target_auth_processing
        ORDER BY corp_num
        LIMIT :sample_size
        """)

        with self.db_engine.connect() as conn:
            totals = conn.execute(totals_sql, params).mappings().first() or {}
            status_rows = conn.execute(statuses_sql, params).mappings().all()
            component_rows = int(conn.execute(component_count_sql, params).scalar() or 0)
            corp_sample = [row['corp_num'] for row in conn.execute(sample_sql, params).mappings().all()]

        return AuthDeleteTrackingCleanupSummary(
            environment=self.environment,
            flow_name=flow_name,
            total_auth_processing_rows=int(totals.get('total_rows') or 0),
            distinct_corp_count=int(totals.get('distinct_corp_count') or 0),
            corp_sample=corp_sample,
            status_counts={row['processed_status']: int(row['row_count'] or 0) for row in status_rows},
            estimated_component_operation_rows=component_rows,
        )

    def execute_delete_tracking_cleanup(
        self,
        selected_corp_nums_sql: str,
        *,
        flow_name: str = AUTH_DELETE_FLOW_NAME,
    ) -> int:
        """Delete matching auth-delete-flow auth_processing rows; FK cascade removes components."""
        target_cte = self._auth_delete_cleanup_target_cte(selected_corp_nums_sql)
        delete_sql = text(target_cte + """
        DELETE FROM auth_processing ap
        USING target_auth_processing target
        WHERE ap.id = target.id
        """)
        with self.db_engine.connect() as conn:
            with conn.begin():
                result = conn.execute(
                    delete_sql,
                    {
                        'environment': self.environment,
                        'flow_name': flow_name,
                    },
                )
                deleted = result.rowcount or 0
        self.logger.info(
            'Deleted %s auth_processing rows for %s/%s cleanup',
            deleted,
            flow_name,
            self.environment,
        )
        return deleted

    def cleanup_full_reset_tracking(
        self,
        corp_num: str,
        *,
        environment: Optional[str] = None,
        preserve_auth_processing_id: Optional[int] = None,
    ) -> int:
        """Delete auth tracking for a corp/environment after a successful full reset.

        When preserve_auth_processing_id is provided, that exact current auth_processing row
        is retained as the durable full-reset sweep marker. auth_component_operation rows for
        deleted auth_processing rows are removed by the FK ON DELETE CASCADE.
        """
        env = environment or self.environment
        query = """
        DELETE FROM auth_processing
        WHERE corp_num = :corp_num
          AND environment = :environment
          AND (:preserve_auth_processing_id IS NULL OR id <> :preserve_auth_processing_id)
        """
        with self.db_engine.connect() as conn:
            with conn.begin():
                result = conn.execute(
                    text(query),
                    {
                        'corp_num': corp_num,
                        'environment': env,
                        'preserve_auth_processing_id': preserve_auth_processing_id,
                    },
                )
                deleted = result.rowcount or 0
        self.logger.info(
            'Deleted %s auth_processing rows for full reset cleanup of %s/%s (preserved id=%s)',
            deleted,
            corp_num,
            env,
            preserve_auth_processing_id,
        )
        return deleted

    def _normalize_component_record(
        self,
        record: AuthComponentOperationRecord | Mapping[str, Any],
    ) -> dict:
        if isinstance(record, AuthComponentOperationRecord):
            return record.as_insert_values(self.environment)

        values = dict(record)
        normalized = {
            'auth_processing_id': values.get('auth_processing_id'),
            'corp_num': values.get('corp_num'),
            'flow_name': values.get('flow_name'),
            'environment': values.get('environment') or self.environment,
            'flow_run_id': values.get('flow_run_id'),
            'operation': _truncate(_enum_value(values.get('operation')), 25),
            'operation_scope': _truncate(_enum_value(values.get('operation_scope')), 25),
            'component': _truncate(_enum_value(values.get('component')), 25),
            'target_type': _truncate(values.get('target_type'), 50),
            'target_value': _truncate(values.get('target_value'), 500),
            'action': _truncate(values.get('action'), 50),
            'status_code': values.get('status_code'),
            'error': _truncate(values.get('error'), 1000),
            'detail': _truncate(values.get('detail'), 2000),
            'dry_run': bool(values.get('dry_run', False)),
        }
        missing = [k for k in ('auth_processing_id', 'corp_num', 'flow_name', 'operation', 'operation_scope', 'component') if not normalized.get(k)]
        if missing:
            raise ValueError(f'Missing required auth component operation fields: {missing}')
        return normalized

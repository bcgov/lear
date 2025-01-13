from enum import Enum
from typing import List
from sqlalchemy import text
import logging

class ProcessingStatuses(str, Enum):
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

class CorpProcessingQueueService:
    def __init__(self, environment: str, db_engine, flow_name: str):
        self.data_load_env = environment
        self.db_engine = db_engine
        self.flow_name = flow_name
        self.logger = logging.getLogger(__name__)

    def reserve_for_flow(self, base_query: str, flow_run_id: str) -> int:
        """Reserve corporations for processing in a specific flow run.

        Args:
            base_query: SQL query that selects corps to be processed
            flow_run_id: Unique identifier for this flow run

        Returns:
            Number of corporations successfully reserved for this flow
        """
        init_query = f"""
        WITH candidate_corps AS ({base_query}),
        available_corps AS (
            SELECT corp_num, corp_type_cd
            FROM candidate_corps
            FOR UPDATE SKIP LOCKED
        )
        INSERT INTO corp_processing (
            corp_num,
            corp_type_cd,
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
            :flow_name,
            :status,
            :environment,
            :flow_run_id,
            NOW(),
            NOW(),
            NULL
        FROM available_corps
        ON CONFLICT (corp_num, flow_name, environment) 
        DO NOTHING
        RETURNING corp_num
        """

        with self.db_engine.connect() as conn:
            with conn.begin():
                result = conn.execute(
                    text(init_query),
                    {
                        'flow_name': self.flow_name,
                        'status': ProcessingStatuses.PENDING,
                        'environment': self.data_load_env,
                        'flow_run_id': flow_run_id
                    }
                )
                count = len(result.fetchall())
                self.logger.info(f"Initialized {count} corps for flow run {flow_run_id}")
                return count

    def claim_batch(self, flow_run_id: str, batch_size: int) -> List[str]:
        """Claim a batch of corporations for immediate processing within a flow run.

        Args:
            flow_run_id: Unique identifier for this flow run
            batch_size: Maximum number of corps to claim

        Returns:
            List of corporation numbers that were successfully claimed for processing
        """
        query = """
        WITH claimable AS (
            SELECT corp_num, id
            FROM corp_processing
            WHERE processed_status = :pending_status
            AND environment = :environment
            AND flow_name = :flow_name
            AND flow_run_id = :flow_run_id
            AND claimed_at IS NULL
            LIMIT :batch_size
            FOR UPDATE SKIP LOCKED
        )
        UPDATE corp_processing
        SET processed_status = :processing_status,
            claimed_at = NOW(),
            last_modified = NOW()
        FROM claimable
        WHERE corp_processing.corp_num = claimable.corp_num
        AND  corp_processing.id = claimable.id
        RETURNING corp_processing.corp_num, corp_processing.claimed_at
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
                claimed = result.fetchall()
                claimed_corps = [row[0] for row in claimed]
                if claimed_corps:
                    self.logger.info(f"Claimed {len(claimed_corps)} corps for flow {flow_run_id}")
                    self.logger.info(f"Corps: {', '.join(claimed_corps[:5])}...")
                    for corp, claimed_at in claimed:
                        self.logger.debug(f"  {corp} claimed at {claimed_at}")
                return claimed_corps

    def update_corp_status(
        self,
        flow_run_id: str,
        corp_num: str,
        status: ProcessingStatuses,
        error: str = None
    ) -> bool:
        """Update status for a corp."""
        query = """
        UPDATE corp_processing
        SET processed_status = :status,
            last_modified = NOW(),
            last_error = CASE 
                WHEN :error IS NOT NULL THEN :error 
                ELSE last_error 
            END
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
                    {
                        'status': status,
                        'error': error,
                        'corp_num': corp_num,
                        'flow_run_id': flow_run_id,
                        'environment': self.data_load_env,
                        'flow_name': self.flow_name
                    }
                )
                success = result.rowcount > 0
                if not success:
                    self.logger.warning(
                        f"Failed to update {corp_num} to {status} "
                        f"(flow_run_id={flow_run_id})"
                    )
                return success

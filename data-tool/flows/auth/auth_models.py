from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class AuthSelectionMode(str, Enum):
    """How an auth flow selects candidate corps to process."""
    MANUAL = "MANUAL"
    MIGRATION_FILTER = "MIGRATION_FILTER"


class AuthDeleteTrackingCleanupMode(str, Enum):
    """Cleanup-only behavior for auth-delete-flow tracking rows."""
    OFF = "OFF"
    PREVIEW = "PREVIEW"
    EXECUTE = "EXECUTE"


class AuthComponentStatus(str, Enum):
    """Per-component outcome stored in auth_processing."""
    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    NOT_RUN = "NOT_RUN"


class AuthOperation(str, Enum):
    """High-level Auth operation identity stored in auth_processing."""
    CREATE = "CREATE"
    UPSERT = "UPSERT"
    DELETE = "DELETE"
    SEND = "SEND"
    RESET = "RESET"


class AuthOperationScope(str, Enum):
    """Auth operation scope stored in auth_processing."""
    ENTITY = "ENTITY"
    CONTACT = "CONTACT"
    AFFILIATION = "AFFILIATION"
    INVITE = "INVITE"
    FULL_ENTITY = "FULL_ENTITY"


class AuthRepeatability(str, Enum):
    """Reservation/attempt policy for auth_processing identity."""
    ONE_SHOT = "ONE_SHOT"
    REPEATABLE = "REPEATABLE"
    RESET = "RESET"


@dataclass(frozen=True)
class AuthRepeatableCampaign:
    """Stable campaign identity for real repeatable auth flows."""
    cycle_key: str
    campaign_scope: str
    attempt_key_context: str
    attempt_key: str
    operation_target: str


@dataclass(frozen=True)
class AuthProcessingIdentity:
    """Complete auth_processing operation identity for one reservation attempt."""
    flow_name: str
    operation: AuthOperation
    operation_scope: AuthOperationScope
    repeatability: AuthRepeatability
    attempt_key_context: str
    attempt_key: str
    dry_run: bool = False
    operation_target: Optional[str] = None
    full_reset_sweep: bool = False

    def as_insert_values(self) -> Dict[str, object]:
        """Return static insert values for auth_processing rows."""
        values: Dict[str, object] = {
            'operation': self.operation.value,
            'operation_scope': self.operation_scope.value,
            'repeatability': self.repeatability.value,
            'attempt_key': self.attempt_key,
            'attempt_key_context': self.attempt_key_context,
            'dry_run': self.dry_run,
        }
        if self.operation_target is not None:
            values['operation_target'] = self.operation_target
        return values


@dataclass(frozen=True)
class AuthCreatePlan:
    """Immutable plan for create-like auth flows."""
    create_entity: bool = True
    upsert_contact: bool = False
    create_affiliations: bool = False
    send_unaffiliated_invite: bool = False
    fail_if_missing_email: bool = False
    dry_run: bool = False
    allow_entity_creation_for_affiliations: bool = True


@dataclass(frozen=True)
class AuthDeletePlan:
    """Immutable plan for delete-like auth flows."""
    delete_affiliations: bool = False
    delete_entity: bool = False
    dry_run: bool = False

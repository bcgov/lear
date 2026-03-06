from dataclasses import dataclass
from enum import Enum


class AuthSelectionMode(str, Enum):
    """How an auth flow selects candidate corps to process."""
    MANUAL = "MANUAL"
    MIGRATION_FILTER = "MIGRATION_FILTER"
    CORP_PROCESSING = "CORP_PROCESSING"


class AuthComponentStatus(str, Enum):
    """Per-component outcome stored in auth_processing."""
    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    NOT_RUN = "NOT_RUN"


@dataclass(frozen=True)
class AuthCreatePlan:
    """Immutable plan for create-like auth flows."""
    create_entity: bool = True
    upsert_contact: bool = False
    create_affiliations: bool = False
    send_unaffiliated_invite: bool = False
    fail_if_missing_email: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class AuthDeletePlan:
    """Immutable plan for delete-like auth flows."""
    delete_affiliations: bool = False
    delete_entity: bool = False
    delete_invites: bool = False  # only if supported by API
    dry_run: bool = False

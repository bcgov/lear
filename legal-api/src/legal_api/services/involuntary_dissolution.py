# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This provides the service for involuntary dissolution."""
from dataclasses import dataclass
from typing import Final, Tuple
from flask import current_app

from sqlalchemy import and_, exists, func, not_, or_, select, text
from sqlalchemy.orm import aliased

from legal_api.models import Batch, BatchProcessing, Business, Filing, db

from .bootstrap import AccountService


class InvoluntaryDissolutionService():
    """Provides services to get information for involuntary dissolution."""

    ELIGIBLE_TYPES: Final = [
        Business.LegalTypes.COMP.value,
        Business.LegalTypes.BC_ULC_COMPANY.value,
        Business.LegalTypes.BC_CCC.value,
        Business.LegalTypes.BCOMP.value,
        Business.LegalTypes.CONTINUE_IN.value,
        Business.LegalTypes.ULC_CONTINUE_IN.value,
        Business.LegalTypes.CCC_CONTINUE_IN.value,
        Business.LegalTypes.BCOMP_CONTINUE_IN.value,
        Business.LegalTypes.EXTRA_PRO_A.value,
        Business.LegalTypes.LIMITED_CO.value
    ]

    @dataclass
    class EligibilityDetails:
        """Details about the eligibility of a business for involuntary dissolution."""

        ar_overdue: bool
        transition_overdue: bool

    @dataclass
    class EligibilityFilters:
        """Details about the exclude of a business for dissolution."""

        exclude_in_dissolution: bool = True
        exclude_future_effective_filing: bool = False

    @classmethod
    def check_business_eligibility(
        cls, identifier: str, eligibility_filters: EligibilityFilters = EligibilityFilters()
    ) -> Tuple[bool, EligibilityDetails]:
        """Return true if the business with provided identifier is eligible for dissolution.

        Returns:
            eligible (bool): True if the business is eligible for dissolution.
            eligibility_details (EligibilityDetails): Details regarding eligibility.
        """
        query = cls._get_businesses_eligible_query(eligibility_filters).filter(Business.identifier == identifier)
        result = query.one_or_none()

        if result is None:
            return False, None

        eligibility_details = cls.EligibilityDetails(ar_overdue=result[1], transition_overdue=result[2])
        return True, eligibility_details

    @classmethod
    def get_businesses_eligible(cls, num_allowed: int = None):
        """Return the businesses eligible for involuntary dissolution."""
        query = cls._get_businesses_eligible_query()
        if num_allowed:
            eligible_businesses = query.limit(num_allowed).all()
        else:
            eligible_businesses = query.all()

        return eligible_businesses

    @classmethod
    def get_businesses_eligible_count(cls):
        """Return the number of businesses eligible for involuntary dissolution."""
        return cls._get_businesses_eligible_query().count()

    @staticmethod
    def get_in_dissolution_batch_processing(business_id: int):
        """Fetch the BatchProcessing record for a business that is in the process of involuntary dissolution."""
        return db.session.query(BatchProcessing, Batch).\
            filter(BatchProcessing.business_id == business_id).\
            filter(BatchProcessing.status.notin_([BatchProcessing.BatchProcessingStatus.COMPLETED,
                                                  BatchProcessing.BatchProcessingStatus.WITHDRAWN])). \
            filter(Batch.id == BatchProcessing.batch_id).\
            filter(Batch.status != Batch.BatchStatus.COMPLETED).\
            filter(Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION).\
            one_or_none()

    @staticmethod
    def _get_businesses_eligible_query(eligibility_filters: EligibilityFilters = EligibilityFilters()):
        """Return SQLAlchemy clause for fetching businesses eligible for involuntary dissolution.

        Args:
            exclude_in_dissolution (bool): If True, exclude businesses already in dissolution.
        """
        in_dissolution = (
            exists().where(
                BatchProcessing.business_id == Business.id,
                BatchProcessing.status.notin_([
                    BatchProcessing.BatchProcessingStatus.WITHDRAWN,
                    BatchProcessing.BatchProcessingStatus.COMPLETED
                ]),
                BatchProcessing.batch_id == Batch.id,
                Batch.status != Batch.BatchStatus.COMPLETED,
                Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION
            )
        )
        specific_filing_overdue = _has_specific_filing_overdue() < func.timezone('UTC', func.now())
        no_transition_filed_after_restoration = func.coalesce((_has_no_transition_filed_after_restoration()
                                                               <= func.timezone('UTC', func.now())), False)

        query = db.session.query(
            Business,
            specific_filing_overdue.label('ar_overdue'),
            no_transition_filed_after_restoration.label('transition_overdue')
        ).\
            filter(not_(Business.admin_freeze.is_(True))).\
            filter(Business.state == Business.State.ACTIVE).\
            filter(Business.legal_type.in_(InvoluntaryDissolutionService.ELIGIBLE_TYPES)).\
            filter(Business.no_dissolution.is_(False))

        future_effective_filing = False if eligibility_filters.exclude_future_effective_filing \
            else _has_future_effective_filing()
        if eligibility_filters.exclude_in_dissolution:
            query = query.filter(not_(in_dissolution))

        query = query.filter(
                or_(
                    specific_filing_overdue,
                    no_transition_filed_after_restoration
                )
            ).\
            filter(
                ~or_(
                    future_effective_filing,
                    _has_delay_of_dissolution_filing(),
                    _is_limited_restored(),
                    _is_xpro_from_nwpta()
                )
            ).\
            order_by(
                no_transition_filed_after_restoration.desc(),
                _has_no_transition_filed_after_restoration().asc(),
                specific_filing_overdue.desc(),
                _has_specific_filing_overdue().asc()
            )

        query = query.filter(_check_feature_flags_filter())

        return query


def _has_specific_filing_overdue():
    """Return SQLAlchemy clause for specific filing overdue check.

    Check if the date of filed recognition(IA)/restoration/annual report
    of the business is over 26 months, whichever is latest.
    """
    from legal_api.core.filing import Filing as CoreFiling  # pylint: disable=import-outside-toplevel

    latest_date = func.greatest(
            Business.founding_date,
            db.session.query(func.max(Filing.effective_date)).filter(
                    Filing.business_id == Business.id,
                    Filing._filing_type.in_([  # pylint: disable=protected-access
                        CoreFiling.FilingTypes.RESTORATION.value,
                        CoreFiling.FilingTypes.RESTORATIONAPPLICATION.value
                    ]),
                    Filing._status == Filing.Status.COMPLETED.value  # pylint: disable=protected-access
                ).scalar_subquery(),
            Business.last_ar_date
        )

    latest_date_cutoff = latest_date + text("""INTERVAL '26 MONTHS'""")

    return latest_date_cutoff


def _has_no_transition_filed_after_restoration():
    """Return SQLAlchemy clause for no transition filed after restoration check.

    Check if the business needs to file Transition but does not file it within 12 months after restoration.
    """
    from legal_api.core.filing import Filing as CoreFiling  # pylint: disable=import-outside-toplevel

    new_act_date = func.date('2004-03-29 00:00:00+00:00')

    restoration_filing = aliased(Filing)
    transition_filing = aliased(Filing)

    restoration_filing_effective_cutoff = restoration_filing.effective_date + text("""INTERVAL '1 YEAR'""")

    return select([func.max(func.coalesce(restoration_filing_effective_cutoff, None))]).where(
            and_(
                Business.legal_type != Business.LegalTypes.EXTRA_PRO_A.value,
                Business.founding_date < new_act_date,
                restoration_filing.business_id == Business.id,
                restoration_filing._filing_type.in_([  # pylint: disable=protected-access
                    CoreFiling.FilingTypes.RESTORATION.value,
                    CoreFiling.FilingTypes.RESTORATIONAPPLICATION.value
                ]),
                restoration_filing._status == Filing.Status.COMPLETED.value,  # pylint: disable=protected-access
                not_(
                    exists().where(
                        and_(
                            transition_filing.business_id == Business.id,
                            transition_filing._filing_type \
                            == CoreFiling.FilingTypes.TRANSITION.value,  # pylint: disable=protected-access
                            transition_filing._status == \
                            Filing.Status.COMPLETED.value,  # pylint: disable=protected-access
                            transition_filing.effective_date.between(
                                restoration_filing.effective_date,
                                restoration_filing_effective_cutoff
                            )
                        )
                    )
                )
            )
        ).scalar_subquery()


def _has_future_effective_filing():
    """Return SQLAlchemy clause for future effective filing check.

    Check if the business has future effective filings.
    """
    # pylint: disable=protected-access
    return db.session.query(Filing). \
        filter(Filing.business_id == Business.id). \
        filter(Filing._status.in_([Filing.Status.PENDING.value, Filing.Status.PAID.value])). \
        exists()


def _has_delay_of_dissolution_filing():
    """Return SQLAlchemy clause for Delay of Dissolution filing check.

    Check if the business has Delay of Dissolution filing.
    """
    # TODO to implement in the future
    return False


def _is_limited_restored():
    """Return SQLAlchemy clause for Limited Restoration check.

    Check if the business is in limited restoration status.
    """
    return and_(
        Business.restoration_expiry_date.isnot(None),
        Business.restoration_expiry_date >= func.timezone('UTC', func.now())
    )


def _is_xpro_from_nwpta():
    """Return SQLAlchemy clause for Expro from NWPTA jurisdictions check.

    Check if the business is extraprovincial and from NWPTA jurisdictions.
    """
    return and_(
        Business.legal_type == Business.LegalTypes.EXTRA_PRO_A.value,
        Business.jurisdiction == 'CA',
        Business.foreign_jurisdiction_region.isnot(None),
        Business.foreign_jurisdiction_region.in_(['AB', 'SK', 'MB'])
    )


def _check_feature_flags_filter():
    """Check eligibility for dissolution based on inclusion and exclusion of businesses."""
    # pylint: disable=E1101
    from . import flags  # pylint: disable=import-outside-toplevel
    # Scenario 1: If the flag is off, proceed with the standard eligibility check.
    if not flags.is_on('enable-involuntary-dissolution-filter'):
        return True  # Continue with the usual logic

    # Get the dissolution filter data (handle if filter is None or empty)
    involuntary_dissolution_filter = flags.value('involuntary-dissolution-filter') or {}

    include_accounts = involuntary_dissolution_filter.get('include-accounts', [])
    exclude_accounts = involuntary_dissolution_filter.get('exclude-accounts', [])

    # Convert accounts to sets for efficient filtering
    include_entities = set(_get_filtered_entities(include_accounts)) if include_accounts else set()
    exclude_entities = set(_get_filtered_entities(exclude_accounts)) if exclude_accounts else set()

    # Scenario 2: Exclude businesses listed in `exclude_accounts`
    if not include_accounts and exclude_accounts:
        return Business.identifier.notin_(list(exclude_entities))

    # Scenario 3: Only include businesses listed in `include_accounts`
    if include_accounts and not exclude_accounts:
        return Business.identifier.in_(list(include_entities))

    # Scenario 4: Include businesses from `include_accounts` but remove those in `exclude_accounts`
    if include_accounts and exclude_accounts:
        eligible_entities = include_entities - exclude_entities  # Remove any overlap between include and exclude
        return Business.identifier.in_(list(eligible_entities))

    return True


def _get_filtered_entities(accounts):
    """Fetch and filter business entities based on the account ID."""
    filtered_entities = []

    for org_id in accounts:
        entities = AccountService.get_affiliations(int(org_id))

        for entity in entities:
            identifier = entity.get('businessIdentifier')
            if identifier and not (identifier.startswith('T') or identifier.startswith('NR')):
                filtered_entities.append(identifier)

    return filtered_entities

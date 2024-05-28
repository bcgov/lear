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
from sqlalchemy import and_, exists, func, not_, or_, text
from sqlalchemy.orm import aliased

from legal_api.models import Batch, BatchProcessing, Business, Filing, db


class InvoluntaryDissolutionService():
    """Provides services to get information for involuntary dissolution."""

    @classmethod
    def check_business_eligibility(cls, identifier: str):
        """Return true if the business with provided identifier is eligible for dissolution."""
        query = cls._get_businesses_eligible_query().\
            filter(Business.identifier == identifier)
        return bool(query.one_or_none())

    @classmethod
    def get_businesses_eligible_count(cls):
        """Return the number of businesses eligible for involuntary dissolution."""
        return cls._get_businesses_eligible_query().count()

    @staticmethod
    def _get_businesses_eligible_query():
        """Return SQLAlchemy clause for fetching businesses eligible for involuntary dissolution."""
        eligible_types = [
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

        subquery = exists().where(BatchProcessing.business_id == Business.id,
                                  BatchProcessing.status.notin_(
                                    [BatchProcessing.BatchProcessingStatus.WITHDRAWN,
                                     BatchProcessing.BatchProcessingStatus.COMPLETED]),
                                  BatchProcessing.batch_id == Batch.id,
                                  Batch.status != Batch.BatchStatus.COMPLETED,
                                  Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION)

        query = db.session.query(Business).\
            filter(Business.state == Business.State.ACTIVE).\
            filter(Business.legal_type.in_(eligible_types)).\
            filter(Business.no_dissolution.is_(False)).\
            filter(not_(subquery)).\
            filter(
                or_(
                    _has_specific_filing_overdue(),
                    _has_no_transition_filed_after_restoration()
                )
            ).\
            filter(
                ~or_(
                    _has_future_effective_filing(),
                    _has_delay_of_dissolution_filing(),
                    _is_limited_restored(),
                    _is_xpro_from_nwpta()
                )
            )

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

    return latest_date_cutoff < func.timezone('UTC', func.now())


def _has_no_transition_filed_after_restoration():
    """Return SQLAlchemy clause for no transition filed after restoration check.

    Check if the business needs to file Transition but does not file it within 12 months after restoration.
    """
    from legal_api.core.filing import Filing as CoreFiling  # pylint: disable=import-outside-toplevel

    new_act_date = func.date('2004-03-29 00:00:00+00:00')

    restoration_filing = aliased(Filing)
    transition_filing = aliased(Filing)

    return exists().where(
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
                                restoration_filing.effective_date + text("""INTERVAL '1 YEAR'""")
                            )
                        )
                    )
                )
            )
        )


def _has_future_effective_filing():
    """Return SQLAlchemy clause for future effective filing check.

    Check if the business has future effective filings.
    """
    return db.session.query(Filing). \
        filter(Filing.business_id == Business.id). \
        filter(Filing._status.in_([Filing.Status.PENDING.value, Filing.Status.PAID.value])). \
        exists()  # pylint: disable=protected-access


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

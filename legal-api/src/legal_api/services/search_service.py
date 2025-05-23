# Copyright © 2025 Province of British Columbia
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

"""This provides the service for getting business details as of a filing."""
# pylint: disable=singleton-comparison ; pylint does not recognize sqlalchemy ==
from dataclasses import dataclass
from datetime import datetime, timezone
from operator import and_
from typing import Final, List, Optional, Tuple

from requests import Request
from sqlalchemy import func

from legal_api.models import Business, Filing, db


@dataclass
class AffiliationSearchDetails:  # pylint: disable=too-many-instance-attributes
    """Used for filtering Identifiers based on filters passed."""

    identifier: Optional[str]
    status: Optional[List[str]]
    name: Optional[str]
    type: Optional[List[str]]
    page: int
    limit: int

    @classmethod
    def from_request_args(cls, req: Request):
        """Create an instance from request arguments."""

        def clean_str(value: Optional[str]) -> Optional[str]:
            return value.strip() if value and value.strip() else None

        def clean_list(values: List[str]) -> List[str]:
            return [v.strip() for v in values if v.strip()]
        return cls(
            identifier=clean_str(req.get('identifier', None)),
            name=clean_str(req.get('name', None)),
            type=clean_list(req.get('type', [])),
            status=clean_list(req.get('status', [])),
            page=int(req.get('page', 1)),
            limit=int(req.get('limit', 100000))
        )


class BusinessSearchService:  # pylint: disable=too-many-public-methods
    """Provides service for getting business and filings details as of a filters."""

    BUSINESS_ELIGIBLE_STATES: Final = [
        Business.State.ACTIVE.value,
        Business.State.HISTORICAL.value,
        Business.State.LIQUIDATION.value
    ]

    FILINGS_ELIGIBLE_STATES: Final = [
        Filing.Status.APPROVED.value,
        Filing.Status.AWAITING_REVIEW.value,
        Filing.Status.CHANGE_REQUESTED.value,
        Filing.Status.DRAFT.value,
        Filing.Status.REJECTED.value,
        Filing.Status.PENDING.value,
        Filing.Status.PAID.value,
        Filing.Status.WITHDRAWN.value
    ]

    # Reverse Mapping for Filing to get filing type from
    # Temp code coming as filter such as: ATMP >>  amalgamationApplication
    BUSINESS_TEMP_FILINGS_CORP_CODES: Final = {
        Filing.FILINGS[filing_type.value]['temporaryCorpTypeCode']: Filing.FILINGS[filing_type.value]['name']
        for filing_type in Filing.TempCorpFilingType
    }

    @staticmethod
    def check_and_get_respective_values(codes):
        """Check if codes belong to BUSINESS_TEMP_FILINGS_CORP_CODES and return the matching ones."""
        return {
            code: BusinessSearchService.BUSINESS_TEMP_FILINGS_CORP_CODES.get(code)
            for code in codes
        }

    @classmethod
    def separate_states_by_type(cls, states: List[str]) -> Tuple[List[str], List[str]]:
        """
        Separates input states into business-eligible and filing-eligible states.

        using human-readable names (e.g. 'Active') and mapping them to enum values.
        """
        input_normalized = [s.upper() for s in states]

        business_name_to_value = {state.name: state.value for state in Business.State}
        filing_name_to_value = {status.name: status.value for status in Filing.Status}

        business_states = [
            business_name_to_value[state]
            for state in input_normalized
            if state in business_name_to_value and business_name_to_value[state] in cls.BUSINESS_ELIGIBLE_STATES
        ]

        filing_states = [
            filing_name_to_value[state]
            for state in input_normalized
            if state in filing_name_to_value and filing_name_to_value[state] in cls.FILINGS_ELIGIBLE_STATES
        ]
        return business_states, filing_states

    @staticmethod
    def try_parse_legal_type(legal_type: str) -> bool:
        """Check if legal type exists in Business.LegalTypes."""
        try:
            Business.LegalTypes(legal_type)
            return True
        except ValueError:
            return False

    @staticmethod
    def separate_legal_types(legal_types: List[str]) -> Tuple[List[str], List[str]]:
        """Separates input legal types into valid and invalid based on the Business.LegalTypes enum."""
        input_normalized = [t.strip().upper() for t in legal_types]

        valid_types = [t for t in input_normalized if BusinessSearchService.try_parse_legal_type(t)]
        invalid_types = [t for t in input_normalized if not BusinessSearchService.try_parse_legal_type(t)]
        return valid_types, invalid_types

    # pylint: disable=too-many-locals
    @staticmethod
    def get_search_filtered_businesses_results(business_json,
                                               identifiers=None,
                                               search_filters: AffiliationSearchDetails = None):
        """Return contact point from business json."""
        name = search_filters.name
        types = search_filters.type
        statuses = search_filters.status
        identifier = search_filters.identifier

        valid_types, _ = BusinessSearchService.separate_legal_types(types or [])

        # Edge case: if type searched for doesnt belong to table business such as 'ATMP' Returns early
        if types and not valid_types:
            return []

        states, _ = BusinessSearchService.separate_states_by_type(statuses or [])

        # If status was provided but none of them are valid, return no results
        if statuses and not states:
            return []
        filters = [
            expr for expr in [
                Business._identifier.in_(identifiers)  # pylint: disable=protected-access
                if identifiers else None,
                Business._identifier.ilike(f'%{identifier}%')  # pylint: disable=protected-access
                if identifier else None,
                Business.legal_name.ilike(f'%{name}%')  # pylint: disable=protected-access
                if name else None,
                Business.legal_type.in_(valid_types)
                if valid_types else None,
                Business.state.in_(states)
                if states else None
            ] if expr is not None
        ]

        if not filters:
            return []

        limit = search_filters.limit or 100
        offset = ((search_filters.page or 1) - 1) * limit
        bus_query = db.session.query(Business).filter(*filters).limit(limit).offset(offset)
        bus_results = []
        for business in bus_query.all():
            business_json = business.json(slim=True)

            if business.legal_type in (
                Business.LegalTypes.SOLE_PROP,
                Business.LegalTypes.PARTNERSHIP
            ):
                business_json['alternateNames'] = business.get_alternate_names()

            bus_results.append(business_json)
        return bus_results

    # pylint: disable=too-many-locals
    @staticmethod
    def get_search_filtered_filings_results(business_json,
                                            identifiers=None,
                                            search_filters: AffiliationSearchDetails = None):
        """Return contact point from business json."""
        name = search_filters.name
        types = search_filters.type
        statuses = search_filters.status
        identifier = search_filters.identifier

        _, valid_types = BusinessSearchService.separate_legal_types(types or [])

        # Edge case: if type searched for doesnt belong to table filings such as 'bc' Returns early
        if types and not valid_types:
            return []

        _, filing_states = BusinessSearchService.separate_states_by_type(statuses or [])
        # If status was provided but none of them are valid, return no results
        if statuses and not filing_states:
            return []

        # Retrieve the corresponding filing name using the BUSINESS_TEMP_FILINGS_CORP_CODES mapping
        filing_name = [
            filing_names
            for filing_names in BusinessSearchService.check_and_get_respective_values(valid_types).values()
            if filing_names is not None
            ]

        filters = [
            expr for expr in [
                and_(Filing.temp_reg.in_(identifiers), Filing.business_id.is_(None))
                if isinstance(identifiers, list) and identifiers else None,
                Filing.temp_reg.ilike(f'%{identifier}%') if identifier else None,
                Filing._status.in_(filing_states) if filing_states else None,  # pylint: disable=protected-access
                Filing._filing_type.in_(filing_name) if filing_name else None,  # pylint: disable=protected-access
                func.jsonb_extract_path_text(
                    Filing._filing_json,  # pylint: disable=protected-access
                    'filing',
                    Filing._filing_type,  # pylint: disable=protected-access
                    'nameRequest',
                    'legalName'
                ).ilike(f'%{name}%') if name else None
            ] if expr is not None
        ]

        limit = search_filters.limit or 100
        offset = ((search_filters.page or 1) - 1) * limit
        draft_query = db.session.query(Filing).filter(*filters).limit(limit).offset(offset)
        draft_results = []
        # base filings query (for draft incorporation/registration filings -- treated as 'draft' business in auth-web)
        if identifiers:
            for draft_dao in draft_query.all():
                draft = {
                    'identifier': draft_dao.temp_reg,  # Temporary registration number of the draft entity
                    'legalType': draft_dao.json_legal_type,  # Legal type of the draft entity
                    'draftType': Filing.FILINGS.get(draft_dao.filing_type, {}).get('temporaryCorpTypeCode'),
                    'draftStatus': draft_dao.status
                }

                if (draft_dao.status == Filing.Status.PAID.value and
                        draft_dao.effective_date and draft_dao.effective_date > datetime.now(timezone.utc)):
                    draft['effectiveDate'] = draft_dao.effective_date.isoformat()

                if draft_dao.json_nr:
                    draft['nrNumber'] = draft_dao.json_nr  # Name request number, if available
                # Retrieves the legal name from the filing JSON. Defaults to None if not found.
                draft['legalName'] = (draft_dao.filing_json.get('filing', {})
                                      .get(draft_dao.filing_type, {})
                                      .get('nameRequest', {})
                                      .get('legalName'))

                if draft['legalName'] is None:
                    # Fallback to a generic legal name based on the legal type if no specific legal name is found
                    draft['legalName'] = (Business.BUSINESSES
                                          .get(draft_dao.json_legal_type, {})
                                          .get('numberedDescription'))
                draft_results.append(draft)

        return draft_results

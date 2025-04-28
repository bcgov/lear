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
from datetime import datetime, timezone
from http import HTTPStatus
from flask import current_app
from operator import and_
from typing import Final

from legal_api.core import filing
from sqlalchemy import or_

from legal_api.models import (
    Business,
    Filing,
    db,
)
from typing import List, Tuple


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

    @classmethod
    def separate_states_by_type(cls, states: List[str]) -> Tuple[List[str], List[str]]:
        """
        Separates input states into business-eligible and filing-eligible states,
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


    def try_parse_legal_type(legal_type: str) -> bool:
        try:
            Business.LegalTypes(legal_type)
            return True
        except ValueError:
            return False

    def separate_legal_types(legal_types: List[str]) -> Tuple[List[str], List[str]]:
        """
        Separates input legal types into valid and invalid based on the Business.LegalTypes enum.
        """
        input_normalized = [t.strip().upper() for t in legal_types]

        valid_types = [t for t in input_normalized if BusinessSearchService.try_parse_legal_type(t)]
        invalid_types = [t for t in input_normalized if not BusinessSearchService.try_parse_legal_type(t)]
        return valid_types, invalid_types

    def paginate(data, page, limit):
            start = (page - 1) * limit
            end = start + limit
            return data[start:end]
    
    @staticmethod
    def get_search_filtered_businesses_results(business_json, identifiers=None, search_filter_name=None, search_filter_type=None,search_filter_status=None):
        """Return contact point from business json."""
        
        filters = []

        if identifiers and isinstance(identifiers, list):
            filters.append(Business._identifier.in_(identifiers))

        if search_filter_name:
            filters.append(Business.legal_name.ilike(f'%{search_filter_name}%'))

        if isinstance(search_filter_type, list):
            valid_filter_values, invalid_filter_values = BusinessSearchService.separate_legal_types(search_filter_type)

            if valid_filter_values:
                filters.append(Business.legal_type.in_(valid_filter_values))
    
        business_states, _ = BusinessSearchService.separate_states_by_type(search_filter_status)

        if search_filter_status and isinstance(search_filter_status, list):
            filters.append(Business.state.in_(business_states))

        if not filters:
            return {}

        try:
            bus_query = db.session.query(Business).filter(*filters)
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

        except Exception as e:
            # Optionally log the error
            current_app.logger.Error(f'Query error: {e}')
            return []
    
    @staticmethod
    def get_search_filtered_filings_results(business_json,
                                            identifiers=None,
                                            search_filter_name=None,
                                            search_filter_type=None,
                                            search_filter_status=None):
        """Return contact point from business json."""
        
        filters = []
        # identifiers
        if identifiers and isinstance(identifiers, list):
            filters.append(and_(Filing.temp_reg.in_(identifiers), Filing.business_id.is_(None)))
        
        # status
        _, filing_states = BusinessSearchService.separate_states_by_type(search_filter_status)
        if search_filter_status and isinstance(search_filter_status, list):
            filters.append(Filing._status.in_(filing_states))

        try:
            draft_query = db.session.query(Filing).filter(*filters)
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
            if search_filter_name:
                draft_results = [
                    draft for draft in draft_results
                    if draft.get('legalName') and search_filter_name.lower() in draft['legalName'].lower()
                ]
            
            if search_filter_type:
                draft_results = [
                    draft for draft in draft_results
                    if draft.get('draftType') in search_filter_type
                ]
            return draft_results

        except Exception as e:
            # Optionally log the error
            current_app.logger.Error(f'Query error: {e}')
            return []
        
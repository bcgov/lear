# Copyright © 2019 Province of British Columbia
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
"""Validation for the Voluntary Dissolution filing."""
from enum import Enum
from http import HTTPStatus
from typing import Dict, Final, Optional

import pycountry
from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Address, Business, PartyRole

from .common_validations import validate_pdf
from ...utils import get_str  # noqa: I003; needed as the linter gets confused from the babel override above.


CORP_TYPES: Final = [Business.LegalTypes.COMP.value,
                     Business.LegalTypes.BCOMP.value,
                     Business.LegalTypes.CCC_CONTINUE_IN.value,
                     Business.LegalTypes.BC_ULC_COMPANY.value]


class DissolutionTypes(str, Enum):
    """Dissolution types."""

    VOLUNTARY = 'voluntary'
    VOLUNTARY_LIQUIDATION = 'voluntaryLiquidation'


class DissolutionStatementTypes(str, Enum):
    """Dissolution statement types."""

    NO_ASSETS_NO_LIABILITIES_197 = '197NoAssetsNoLiabilities'
    NO_ASSETS_PROVISIONS_LIABILITIES_197 = '197NoAssetsProvisionsLiabilities'

    @classmethod
    def has_value(cls, value):
        """Check if enum contains specific value provided via input param."""
        return value in cls._value2member_map_  # pylint: disable=no-member


DISSOLUTION_MAPPING = {
    'COOP': [DissolutionTypes.VOLUNTARY, DissolutionTypes.VOLUNTARY_LIQUIDATION],
    'CORP': [DissolutionTypes.VOLUNTARY]
}


def validate(business: Business, con: Dict) -> Optional[Error]:
    """Validate the dissolution filing."""
    if not business or not con:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])

    legal_type = get_str(con, '/filing/business/legalType')
    msg = []

    err = validate_dissolution_type(con, legal_type)
    if err:
        msg.extend(err)

    err = validate_dissolution_statement_type(con, legal_type)
    if err:
        msg.extend(err)

    err = validate_parties_address(con, legal_type)
    if err:
        msg.extend(err)

    err = validate_documents(con, legal_type)
    if err:
        msg.extend(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_dissolution_type(filing_json, legal_type) -> Optional[list]:
    """Validate dissolution type of the filing."""
    msg = []
    dissolution_type_path = '/filing/dissolution/dissolutionType'
    dissolution_type = get_str(filing_json, dissolution_type_path)
    if dissolution_type:
        if (legal_type == Business.LegalTypes.COOP.value and dissolution_type not in DISSOLUTION_MAPPING['COOP']) \
                or (legal_type in CORP_TYPES and dissolution_type not in DISSOLUTION_MAPPING['CORP']):
            msg.append({'error': _('Invalid Dissolution type.'), 'path': dissolution_type_path})
            return msg
    else:
        msg.append({'error': _('Dissolution type must be provided.'),
                    'path': dissolution_type_path})
        return msg

    return None


def validate_dissolution_statement_type(filing_json, legal_type) -> Optional[list]:
    """Validate dissolution statement type of the filing."""
    msg = []
    dissolution_stmt_type_path = '/filing/dissolution/dissolutionStatementType'
    dissolution_stmt_type = get_str(filing_json, dissolution_stmt_type_path)

    if legal_type == Business.LegalTypes.COOP.value:
        if not dissolution_stmt_type:
            msg.append({'error': _('Dissolution statement type must be provided.'),
                        'path': dissolution_stmt_type_path})
            return msg
        if not DissolutionStatementTypes.has_value(dissolution_stmt_type):
            msg.append({'error': _('Invalid Dissolution statement type.'),
                        'path': dissolution_stmt_type_path})
            return msg

    return None


def validate_parties_address(filing_json, legal_type) -> Optional[list]:
    """Validate the person data of the dissolution filing.

    Address must be in Canada for COOP and BC for CORP.
    Both mailing and delivery address are mandatory.
    """
    parties_json = filing_json['filing']['dissolution']['parties']
    parties = list(filter(lambda x: _is_dissolution_party_role(x.get('roles', [])), parties_json))
    msg = []
    address_in_bc = 0
    address_in_ca = 0
    party_path = '/filing/dissolution/parties'

    if len(parties) > 0:
        err, address_in_bc, address_in_ca = _validate_address_location(parties)
        if err:
            msg.extend(err)
    else:
        msg.append({'error': 'Dissolution party is required.', 'path': party_path})

    if legal_type == Business.LegalTypes.COOP.value and address_in_ca == 0:
        msg.append({'error': 'Address must be in Canada.', 'path': party_path})
    elif legal_type in CORP_TYPES and address_in_bc == 0:
        msg.append({'error': 'Address must be in BC.', 'path': party_path})

    if msg:
        return msg

    return None


def _is_dissolution_party_role(roles: list) -> bool:
    return any(role.get('roleType', '').lower() in
               [PartyRole.RoleTypes.CUSTODIAN.value,
                PartyRole.RoleTypes.LIQUIDATOR.value] for role in roles)


def _validate_address_location(parties):
    msg = []
    address_in_bc = 0
    address_in_ca = 0
    for idx, party in enumerate(parties):  # pylint: disable=too-many-nested-blocks;  # noqa: E501
        for address_type in Address.JSON_ADDRESS_TYPES:
            if address_type in party:
                try:
                    region = get_str(party, f'/{address_type}/addressRegion')
                    if region == 'BC':
                        address_in_bc += 1

                    country = get_str(party, f'/{address_type}/addressCountry')
                    country_code = pycountry.countries.search_fuzzy(country)[0].alpha_2
                    if country_code == 'CA':
                        address_in_ca += 1

                except LookupError:
                    msg.append({'error': _('Address Country must resolve to a valid ISO-2 country.'),
                                'path': f'/filing/dissolution/parties/{idx}/{address_type}/addressCountry'})
            else:
                msg.append({'error': _(f'{address_type} is required.'),
                            'path': f'/filing/dissolution/parties/{idx}'})

    if msg:
        return msg, address_in_bc, address_in_ca

    return None, address_in_bc, address_in_ca


def validate_documents(filing_json, legal_type) -> Optional[list]:
    """Validate documents of the filing."""
    msg = []

    if legal_type == Business.LegalTypes.COOP.value:
        affidavit_file_key = filing_json['filing']['dissolution'].get('affidavitFileKey', None)
        affidavit_file_name = filing_json['filing']['dissolution'].get('affidavitFileName', None)
        special_resolution_file_key = filing_json['filing']['dissolution'].get('specialResolutionFileKey', None)
        special_resolution_file_name = filing_json['filing']['dissolution'].get('specialResolutionFileName', None)

        # Validate key values exist
        if not affidavit_file_key:
            msg.append({'error': _('A valid affidavit key is required.'),
                        'path': '/filing/dissolution/affidavitFileKey'})

        if not affidavit_file_name:
            msg.append({'error': _('A valid affidavit file name is required.'),
                        'path': '/filing/dissolution/affidavitFileName'})

        if not special_resolution_file_key:
            msg.append({'error': _('A valid special resolution key is required.'),
                        'path': '/filing/dissolution/specialResolutionFileKey'})

        if not special_resolution_file_name:
            msg.append({'error': _('A valid special resolution file name is required.'),
                        'path': '/filing/dissolution/specialResolutionFileName'})

        if msg:
            return msg

        affidavit_err = validate_pdf(affidavit_file_key, '/filing/dissolution/affidavitFileKey')
        if affidavit_err:
            return affidavit_err

        special_resolution_err = validate_pdf(special_resolution_file_key,
                                              '/filing/dissolution/specialResolutionFileKey')
        if special_resolution_err:
            return special_resolution_err

    return None

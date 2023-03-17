# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Common validations share through the different filings."""
import io
from datetime import datetime
from typing import Optional

import PyPDF2
from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services import MinioService, namex
from legal_api.services.utils import get_str
from legal_api.utils.datetime import datetime as dt


def has_at_least_one_share_class(filing_json, filing_type) -> Optional[str]:  # pylint: disable=too-many-branches
    """Ensure that share structure contain at least 1 class by the end of the alteration or IA Correction filing."""
    if filing_type in filing_json['filing'] and 'shareStructure' in filing_json['filing'][filing_type]:
        share_classes = filing_json['filing'][filing_type] \
            .get('shareStructure', {}).get('shareClasses', [])

        if len(share_classes) == 0:
            return 'A company must have a minimum of one share class.'

    return None


def validate_resolution_date_in_share_structure(filing_json, filing_type) -> Optional[dict]:
    """Has resolution date in share structure when hasRightsOrRestrictions is true."""
    share_structure = filing_json['filing'][filing_type].get('shareStructure', {})
    share_classes = share_structure.get('shareClasses', [])
    if any(x.get('hasRightsOrRestrictions', False) for x in share_classes) or \
            any(has_rights_or_restrictions_true_in_share_series(x) for x in share_classes):
        if len(share_structure.get('resolutionDates', [])) == 0:
            return {
                'error': 'Resolution date is required when hasRightsOrRestrictions is true in shareClasses.',
                'path': f'/filing/{filing_type}/shareStructure/resolutionDates'
            }
    return None


def has_rights_or_restrictions_true_in_share_series(share_class) -> bool:
    """Has hasRightsOrRestrictions is true in series."""
    series = share_class.get('series', [])
    return any(x.get('hasRightsOrRestrictions', False) for x in series)


def validate_share_structure(incorporation_json, filing_type) -> Error:  # pylint: disable=too-many-branches
    """Validate the share structure data of the incorporation filing."""
    share_classes = incorporation_json['filing'][filing_type] \
        .get('shareStructure', {}).get('shareClasses', [])
    msg = []
    memoize_names = []

    for index, item in enumerate(share_classes):
        shares_msg = validate_shares(item, memoize_names, filing_type, index)
        if shares_msg:
            msg.extend(shares_msg)

    if msg:
        return msg

    return None


def validate_series(item, memoize_names, filing_type, index) -> Error:
    """Validate shareStructure includes a wellformed series."""
    msg = []
    for series_index, series in enumerate(item.get('series', [])):
        err_path = '/filing/{0}/shareClasses/{1}/series/{2}'.format(filing_type, index, series_index)
        if series['name'] in memoize_names:
            msg.append({'error': 'Share series %s name already used in a share class or series.' % series['name'],
                        'path': err_path})
        else:
            memoize_names.append(series['name'])

        if series['hasMaximumShares']:
            if not series.get('maxNumberOfShares', None):
                msg.append({
                    'error': 'Share series %s must provide value for maximum number of shares' % series['name'],
                    'path': '%s/maxNumberOfShares' % err_path
                })
            else:
                if item['hasMaximumShares'] and item.get('maxNumberOfShares', None) and \
                        int(series['maxNumberOfShares']) > int(item['maxNumberOfShares']):
                    msg.append({
                        'error': 'Series %s share quantity must be less than or equal to that of its class %s'
                                 % (series['name'], item['name']),
                        'path': '%s/maxNumberOfShares' % err_path
                    })
    return msg


def validate_shares(item, memoize_names, filing_type, index) -> Error:
    """Validate a wellformed share structure."""
    msg = []
    if item['name'] in memoize_names:
        err_path = '/filing/{0}/shareClasses/{1}/name/'.format(filing_type, index)
        msg.append({'error': 'Share class %s name already used in a share class or series.' % item['name'],
                    'path': err_path})
    else:
        memoize_names.append(item['name'])

    if item['hasMaximumShares'] and not item.get('maxNumberOfShares', None):
        err_path = '/filing/{0}/shareClasses/{1}/maxNumberOfShares/'.format(filing_type, index)
        msg.append({'error': 'Share class %s must provide value for maximum number of shares' % item['name'],
                    'path': err_path})
    if item['hasParValue']:
        if not item.get('parValue', None):
            err_path = '/filing/{0}/shareClasses/{1}/parValue/'.format(filing_type, index)
            msg.append({'error': 'Share class %s must specify par value' % item['name'], 'path': err_path})
        if not item.get('currency', None):
            err_path = '/filing/{0}/shareClasses/{1}/currency/'.format(filing_type, index)
            msg.append({'error': 'Share class %s must specify currency' % item['name'], 'path': err_path})

    series_msg = validate_series(item, memoize_names, filing_type, index)
    if series_msg:
        msg.extend(series_msg)

    return msg


def validate_court_order(court_order_path, court_order):
    """Validate the courtOrder data of the filing."""
    msg = []

    # TODO remove it when the issue with schema validation is fixed
    if 'fileNumber' not in court_order:
        err_path = court_order_path + '/fileNumber'
        msg.append({'error': 'Court order file number is required.', 'path': err_path})
    else:
        if len(court_order['fileNumber']) < 5 or len(court_order['fileNumber']) > 20:
            err_path = court_order_path + '/fileNumber'
            msg.append({'error': 'Length of court order file number must be from 5 to 20 characters.',
                        'path': err_path})

    if (effect_of_order := court_order.get('effectOfOrder', None)) and effect_of_order != 'planOfArrangement':
        msg.append({'error': 'Invalid effectOfOrder.', 'path': f'{court_order_path}/effectOfOrder'})

    court_order_date_path = court_order_path + '/orderDate'
    if 'orderDate' in court_order:
        try:
            court_order_date = dt.fromisoformat(court_order['orderDate'])
            if court_order_date.timestamp() > datetime.utcnow().timestamp():
                err_path = court_order_date_path
                msg.append({'error': 'Court order date cannot be in the future.', 'path': err_path})
        except ValueError:
            err_path = court_order_date_path
            msg.append({'error': 'Invalid court order date format.', 'path': err_path})

    if msg:
        return msg

    return None


def validate_pdf(file_key: str, file_key_path: str) -> Optional[list]:
    """Validate the PDF file."""
    msg = []
    try:
        file = MinioService.get_file(file_key)
        open_pdf_file = io.BytesIO(file.data)
        pdf_reader = PyPDF2.PdfFileReader(open_pdf_file)

        # Check that all pages in the pdf are letter size and able to be processed.
        if any(x.mediaBox.getWidth() != 612 or x.mediaBox.getHeight() != 792 for x in pdf_reader.pages):
            msg.append({'error': _('Document must be set to fit onto 8.5” x 11” letter-size paper.'),
                        'path': file_key_path})

        file_info = MinioService.get_file_info(file_key)
        if file_info.size > 30000000:
            msg.append({'error': _('File exceeds maximum size.'), 'path': file_key_path})

        if pdf_reader.isEncrypted:
            msg.append({'error': _('File must be unencrypted.'), 'path': file_key_path})

    except Exception:
        msg.append({'error': _('Invalid file.'), 'path': file_key_path})

    if msg:
        return msg

    return None


def validate_party_name(legal_type: str, party: dict, party_path: str) -> list:
    """Validate party name."""
    msg = []

    custom_allowed_max_length = 20
    officer = party['officer']
    party_type = officer['partyType']

    if party_type == 'person' and legal_type in [Business.LegalTypes.BCOMP.value, Business.LegalTypes.COOP.value]:
        party_roles = [x.get('roleType') for x in party['roles']]
        party_roles_str = ', '.join(party_roles)

        first_name = officer['firstName']
        if len(first_name) > custom_allowed_max_length:
            err_msg = f'{party_roles_str} first name cannot be longer than {custom_allowed_max_length} characters'
            msg.append({'error': err_msg, 'path': party_path})

        if 'middleInitial' in officer \
                and (middle_initial := officer['middleInitial']) \
                and len(middle_initial) > custom_allowed_max_length:
            err_msg = f'{party_roles_str} middle initial cannot be longer than {custom_allowed_max_length} characters'
            msg.append({'error': err_msg, 'path': party_path})

        if 'middleName' in officer \
                and (middle_name := officer['middleName']) \
                and len(middle_name) > custom_allowed_max_length:
            err_msg = f'{party_roles_str} middle name cannot be longer than {custom_allowed_max_length} characters'
            msg.append({'error': err_msg, 'path': party_path})

    return msg


def validate_name_request(filing_json: dict,  # pylint: disable=too-many-locals
                          legal_type: str,
                          filing_type: str,
                          accepted_request_types: list = None) -> list:
    """Validate name request section."""
    nr_path = f'/filing/{filing_type}/nameRequest'
    nr_number_path = f'{nr_path}/nrNumber'
    legal_name_path = f'{nr_path}/legalName'
    legal_type_path = f'{nr_path}/legalType'

    nr_number = get_str(filing_json, nr_number_path)
    legal_name = get_str(filing_json, legal_name_path)

    valid_numbered_legal_type = [Business.LegalTypes.BCOMP.value,
                                 Business.LegalTypes.COMP.value,
                                 Business.LegalTypes.BC_CCC.value,
                                 Business.LegalTypes.BC_ULC_COMPANY.value]
    if not nr_number and not legal_name:
        if legal_type in valid_numbered_legal_type:
            return []  # It's numbered company
        else:
            # CP, SP, GP doesn't support numbered company
            return [{'error': _('Legal name and nrNumber is missing in nameRequest.'), 'path': nr_path}]
    elif nr_number and not legal_name:
        return [{'error': _('Legal name is missing in nameRequest.'), 'path': legal_name_path}]
    elif not nr_number and legal_name:
        # expecting nrNumber when legalName provided
        return [{
            'error': _('nrNumber is missing for the legal name provided in nameRequest.'),
            'path': nr_number_path
        }]

    msg = []
    # ensure NR is approved or conditionally approved
    nr_response = namex.query_nr_number(nr_number)
    nr_response_json = nr_response.json()
    validation_result = namex.validate_nr(nr_response_json)
    if not validation_result['is_consumable']:
        msg.append({'error': _('Name Request is not approved.'), 'path': nr_number_path})

    # ensure NR request type code
    if accepted_request_types and not nr_response_json['requestTypeCd'] in accepted_request_types:
        msg.append({'error': _('The name type associated with the name request number entered cannot be used.'),
                    'path': nr_number_path})

    # ensure business type
    nr_legal_type = nr_response_json.get('legalType')
    if legal_type != nr_legal_type:
        msg.append({'error': _('Name Request legal type is not same as the business legal type.'),
                    'path': legal_type_path})

    # ensure NR request has the same legal name
    nr_name = namex.get_approved_name(nr_response_json)
    if nr_name != legal_name:
        msg.append({'error': _('Name Request legal name is not same as the business legal name.'),
                    'path': legal_name_path})

    return msg

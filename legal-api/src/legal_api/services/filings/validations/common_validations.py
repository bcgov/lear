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
import re
from datetime import datetime, timedelta
from typing import Dict, Optional

import pycountry
import PyPDF2
from flask import current_app, g
from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Address, Business, Party, PartyRole
from legal_api.services import MinioService, flags, namex
from legal_api.services.utils import get_str, get_clean_str
from legal_api.utils.datetime import datetime as dt


NO_POSTAL_CODE_COUNTRY_CODES = {
    'AO', 'AG', 'AW', 'BS', 'BZ', 'BJ', 'BM', 'BO', 'BQ', 'BW', 'BF', 'BI',
    'CM', 'CF', 'TD', 'KM', 'CG', 'CD', 'CK', 'CI', 'CW', 'DJ', 'DM', 'GQ',
    'ER', 'FJ', 'TF', 'GA', 'GM', 'GH', 'GD', 'GY', 'HM', 'HK',
    'KI', 'KP', 'LY', 'MO', 'MW', 'ML', 'MR', 'NR',
    'AN', 'NU', 'QA', 'RW', 'KN', 'ST', 'SC', 'SL', 'SX', 'SB', 'SO', 'SR', 'SY',
    'TL', 'TG', 'TK', 'TO', 'TT', 'TV', 'UG', 'AE', 'VU', 'YE', 'ZW'
}


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


def validate_share_structure(incorporation_json, filing_type, legal_type) -> Error:  # pylint: disable=too-many-branches
    """Validate the share structure data of the incorporation filing."""
    share_classes = incorporation_json['filing'][filing_type] \
        .get('shareStructure', {}).get('shareClasses', [])
    msg = []
    memoize_names = []

    for index, item in enumerate(share_classes):
        shares_msg = validate_shares(item, memoize_names, filing_type, index, legal_type)
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

        raw_series_name = series.get('name', '')
        cleaned_series_name = raw_series_name.strip()
        series['name'] = cleaned_series_name

        if not cleaned_series_name:
            msg.append({
                'error': 'Share series name cannot be empty or only whitespace',
                'path': f'{err_path}/name/'
            })

        if cleaned_series_name in memoize_names:
            msg.append({'error': 'Share series %s name already used in a share class or series.' % cleaned_series_name,
                        'path': err_path})
        else:
            memoize_names.append(cleaned_series_name)

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


def validate_shares(item, memoize_names, filing_type, index, legal_type) -> Error:
    """Validate a wellformed share structure."""
    msg = []

    raw_name = item.get('name', '')
    cleaned_name = raw_name.strip()
    item['name'] = cleaned_name

    if not cleaned_name:
        err_path = '/filing/{0}/shareClasses/{1}/name/'.format(filing_type, index)
        msg.append({
            'error': 'Share class name cannot be empty or only whitespace',
            'path': err_path
        })

    if cleaned_name in memoize_names:
        err_path = '/filing/{0}/shareClasses/{1}/name/'.format(filing_type, index)
        msg.append({'error': 'Share class %s name already used in a share class or series.' % cleaned_name,
                    'path': err_path})
    else:
        memoize_names.append(cleaned_name)

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

    # Validate that corps type companies cannot have series in share classes when hasRightsOrRestrictions is false
    if legal_type in Business.CORPS:
        series = item.get('series', [])
        has_series = False
        if len(series) > 0:
            has_series = True

        if not item.get('hasRightsOrRestrictions', False) and has_series:
            err_path = '/filing/{0}/shareClasses/{1}/series/'.format(filing_type, index)
            msg.append({
                'error': 'Share class %s cannot have series when hasRightsOrRestrictions is false' % item['name'],
                'path': err_path
            })
            return msg

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


def validate_pdf(file_key: str, file_key_path: str, verify_paper_size: bool = True) -> Optional[list]:
    """Validate the PDF file."""
    msg = []
    try:
        file = MinioService.get_file(file_key)
        open_pdf_file = io.BytesIO(file.data)
        pdf_reader = PyPDF2.PdfFileReader(open_pdf_file)

        if verify_paper_size:
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


def validate_parties_names(filing_json: dict, filing_type: str, legal_type: str) -> list:
    """Validate the parties name for COLIN sync."""
    # FUTURE: This validation should be removed when COLIN sync back is no longer required.
    # This is required to work around first and middle name length mismatches between LEAR and COLIN.
    # Syncing back to COLIN would error out on first and middle name length exceeding 20 characters for party
    msg = []
    parties_array = filing_json['filing'][filing_type]['parties']
    party_path = f'/filing/{filing_type}/parties'

    for item in parties_array:
        msg.extend(validate_party_name(item, party_path, legal_type))

    return msg


def validate_party_name(party: dict, party_path: str, legal_type: str) -> list:
    """Validate party name."""
    msg = []

    custom_allowed_max_length = 20
    last_name_max_length = 30
    officer = party['officer']
    party_type = officer['partyType']

    if party_type == 'person':
        party_roles = [x.get('roleType') for x in party['roles']]
        party_roles_str = ', '.join(party_roles)

        first_name = officer.get('firstName', None)
        if (legal_type in Business.CORPS) and (not first_name):
            msg.append({'error': f'{party_roles_str} first name is required', 'path': f'{party_path}'})
            return msg
        trimmed_first = get_clean_str(first_name)
        officer['firstName'] = trimmed_first
        if not trimmed_first:
            msg.append({
                'error': f'{party_roles_str} first name cannot be only whitespace',
                'path': party_path
            })    
        elif len(first_name) > custom_allowed_max_length:
            err_msg = f'{party_roles_str} first name cannot be longer than {custom_allowed_max_length} characters'
            msg.append({'error': err_msg, 'path': party_path})

        middle_initial = officer.get('middleInitial')
        if middle_initial:
            trimmed_initial = get_clean_str(middle_initial)
            officer['middleInitial'] = trimmed_initial
            if not trimmed_initial:
                msg.append({'error': f'{party_roles_str} middle initial cannot be only whitespace',
                             'path': party_path})
            elif len(trimmed_initial) > custom_allowed_max_length:
                err_msg = f'{party_roles_str} middle initial cannot be longer than {custom_allowed_max_length} characters'
                msg.append({'error': err_msg, 'path': party_path})    

        middle_name = officer.get('middleName')
        if middle_name:
            trimmed_middle = get_clean_str(middle_name)
            officer['middleName'] = trimmed_middle
            if not trimmed_middle:
                msg.append({'error': f'{party_roles_str} middle name cannot be only whitespace',
                             'path': party_path})
            elif len(trimmed_middle) > custom_allowed_max_length:
                err_msg = f'{party_roles_str} middle name cannot be longer than {custom_allowed_max_length} characters'
                msg.append({'error': err_msg, 'path': party_path})

        last_name = officer.get('lastName', None)
        if (legal_type in Business.CORPS) and (not last_name):
            msg.append({'error': f'{party_roles_str} last name is required', 'path': f'{party_path}'})
            return msg
        trimmed_last = get_clean_str(last_name)
        officer['lastName'] = trimmed_last
        if not trimmed_last:
            msg.append({
                'error': f'{party_roles_str} last name cannot be only whitespace',
                'path': party_path
            })    
        elif len(last_name) > last_name_max_length:
            err_msg = f'{party_roles_str} last name cannot be longer than {last_name_max_length} characters'
            msg.append({'error': err_msg, 'path': party_path})  

    return msg 


def validate_name_request(filing_json: dict,  # pylint: disable=too-many-locals
                          legal_type: str,
                          filing_type: str,
                          accepted_request_types: list = None) -> list:
    """Validate name request section."""
    # This is added specifically for the sandbox environment.
    # i.e. NR check should only ever have feature flag disabled for sandbox environment.
    if flags.is_on('enable-sandbox'):
        current_app.logger.debug('Skipping name request validation for Sandbox.')
        return []

    nr_path = f'/filing/{filing_type}/nameRequest'
    nr_number_path = f'{nr_path}/nrNumber'
    legal_name_path = f'{nr_path}/legalName'
    legal_type_path = f'{nr_path}/legalType'

    nr_number = get_str(filing_json, nr_number_path)
    legal_name = get_str(filing_json, legal_name_path)

    if not nr_number and not legal_name:
        if legal_type in Business.CORPS:
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
    if accepted_request_types and nr_response_json['requestTypeCd'] not in accepted_request_types:
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


def validate_foreign_jurisdiction(foreign_jurisdiction: dict,
                                  foreign_jurisdiction_path: str,
                                  is_region_bc_valid=False,
                                  is_region_for_us_required=True) -> list:
    """Validate foreign jurisdiction."""
    msg = []
    country_code = foreign_jurisdiction.get('country').upper()  # country is a required field in schema
    region = (foreign_jurisdiction.get('region') or '').upper()

    country = pycountry.countries.get(alpha_2=country_code)
    if not country:
        msg.append({'error': 'Invalid country.', 'path': f'{foreign_jurisdiction_path}/country'})
    elif country_code == 'CA':
        if not is_region_bc_valid and region == 'BC':
            msg.append({'error': 'Region should not be BC.', 'path': f'{foreign_jurisdiction_path}/region'})
        elif not (region == 'FEDERAL' or pycountry.subdivisions.get(code=f'{country_code}-{region}')):
            msg.append({'error': 'Invalid region.', 'path': f'{foreign_jurisdiction_path}/region'})
    elif (country_code == 'US' and
          is_region_for_us_required and
          not pycountry.subdivisions.get(code=f'{country_code}-{region}')):
        msg.append({'error': 'Invalid region.', 'path': f'{foreign_jurisdiction_path}/region'})

    return msg


def validate_offices_addresses(filing_json: dict, filing_type: str) -> list:
    """Validate optional fields in office addresses."""
    msg = []
    offices_dict = filing_json['filing'][filing_type]['offices']
    offices_path = f'/filing/{filing_type}/offices'
    for key, value in offices_dict.items():
        msg.extend(validate_addresses(value, f'{offices_path}/{key}'))
    return msg


def validate_parties_addresses(filing_json: dict, filing_type: str, key: str = 'parties') -> list:
    """Validate optional fields in party addresses."""
    msg = []
    parties_array = filing_json['filing'][filing_type][key]
    parties_path = f'/filing/{filing_type}/{key}'
    for idx, party in enumerate(parties_array):
        msg.extend(validate_addresses(party, f'{parties_path}/{idx}'))
    return msg


def validate_addresses(
    addresses: dict,
    addresses_path: str
) -> list:
    """Validate optional fields in addresses."""
    msg = []
    for address_type in Address.JSON_ADDRESS_TYPES:
        if address := addresses.get(address_type):
            err = _validate_postal_code(address, f'{addresses_path}/{address_type}')
            if err:
                msg.append(err)
    return msg


def _validate_postal_code(
    address: dict,
    address_path: str
) -> dict:
    """Validate that postal code is optional for specified country."""
    country = address['addressCountry']
    postal_code = address.get('postalCode')
    try:
        country = pycountry.countries.search_fuzzy(country)[0].alpha_2
        if country not in NO_POSTAL_CODE_COUNTRY_CODES and\
                not postal_code:
            return {'error': _('Postal code is required.'),
                    'path': f'{address_path}/postalCode'}
    except LookupError:
        # Different ISO-2 country validations are done at filing level,
        # this can be refactored into a common validator in the future
        return None

    return None


def validate_phone_number(filing_json: Dict, legal_type: str, filing_type: str) -> list:
    """Validate phone number."""
    if legal_type not in Business.CORPS:
        return []

    contact_point_path = f'/filing/{filing_type}/contactPoint'
    contact_point_dict = filing_json['filing'][filing_type].get('contactPoint', {})

    msg = []
    if phone_num := contact_point_dict.get('phone', None):
        # if pure digits (max 10)
        if phone_num.isdigit():
            if len(phone_num) != 10:
                msg.append({
                    'error': 'Invalid phone number, maximum 10 digits in phone number format',
                    'path': f'{contact_point_path}/phone'})
        else:
            # Check various phone formats
            # (123) 456-7890 / 123-456-7890 / 123.456.7890 / 123 456 7890
            phone_pattern = r'^\(?\d{3}[\)\-\.\s]?\s?\d{3}[\-\.\s]\d{4}$'
            if not re.match(phone_pattern, phone_num):
                msg.append({
                    'error': 'Invalid phone number, maximum 10 digits in phone number format',
                    'path': f'{contact_point_path}/phone'})

    if extension := contact_point_dict.get('extension'):
        if len(str(extension)) > 5:
            msg.append({'error': 'Invalid extension, maximum 5 digits', 'path': f'{contact_point_path}/extension'})

    return msg

def validate_effective_date(filing_json: dict) -> list:
    """Validate effective date"""
    msg = []

    now = dt.utcnow() 
    min_allowed = now + timedelta(minutes=2)
    max_allowed = now + timedelta(days=10)

    filing_effective_date = filing_json.get('filing', {}).get('header', {}).get('effectiveDate')
    if not filing_effective_date:
        return msg

    try:
        effective_date = datetime.fromisoformat(filing_effective_date)
    except ValueError:
        msg.append({'error': f'{filing_effective_date} is an invalid ISO format for effectiveDate.',
                    'path': '/filing/header/effectiveDate'})
        return msg

    if effective_date < min_allowed:
        msg.append({'error': 'Invalid Datetime, effective date must be a minimum of 2 minutes ahead.',
                    'path': '/filing/header/effectiveDate'})
        return msg            

    if effective_date > max_allowed:
        msg.append({'error': 'Invalid Datetime, effective date must be a maximum of 10 days ahead.',
                    'path': '/filing/header/effectiveDate'})
        return msg            

    return msg

def find_updated_keys_for_firms(business: Business, filing_json: dict, filing_type) -> list:
    """Find updated keys in the firm filing (replace, add, edit email, etc.)."""
    updated_keys = []
    if business.legal_type == Business.LegalTypes.SOLE_PROP.value:
        role_type = PartyRole.RoleTypes.PROPRIETOR.value
    elif business.legal_type == Business.LegalTypes.PARTNERSHIP.value:
        role_type = PartyRole.RoleTypes.PARTNER.value
    else:
        return updated_keys

    # Get business and existing parties from DB
    db_party_roles = PartyRole.get_parties_by_role(business.id, role_type)
    parties = filing_json['filing'][filing_type].get('parties', [])

    matched_db_parties = set()

    for party in parties:
        roles = party.get("roles", [])
        has_matching_role = any(role.get("roleType") == role_type for role in roles)
        if not has_matching_role:
            continue
        officer = party.get("officer", {})
        email = officer.get("email")
        mailing_address = party.get("mailingAddress", {})
        delivery_address = party.get("deliveryAddress", {})

        # Match with existing DB party
        matched_db_party = None
        party_id = party.get("officer", {}).get("id")

        if party_id:
            for role in db_party_roles:
                if role.party_id == party_id and role.party_id not in matched_db_parties:
                    matched_db_party = role.party
                    if matched_db_party:
                        matched_db_parties.add(role.party_id)
                        break
       
        if matched_db_party:
            changes = {}
            # Email comparison
            if not is_same_str(email, matched_db_party.email):
                changes['email'] = {
                    'old': normalize_str(matched_db_party.email),
                    'new': normalize_str(email)
                }
            
            old_name = {
                    'firstName': matched_db_party.first_name,
                    'middleName': matched_db_party.middle_initial,
                    'lastName': matched_db_party.last_name,
                    'organizationName': matched_db_party.organization_name
                }
            new_name = {
                'firstName': officer.get('firstName'),
                'middleName': officer.get('middleName'),
                'lastName': officer.get('lastName'),
                'organizationName': officer.get('organizationName')
            }
          
            name_changed = is_name_changed(old_name, new_name)
            changes['name'] = {
                'old': old_name,
                'new': new_name,
                'changed': name_changed
            }
            # Mailing address comparison
            db_mailing_address = (Address.find_by_id(matched_db_party.mailing_address_id)
                                  if matched_db_party.mailing_address_id else None)
            old_mailing = {
                'streetAddress': db_mailing_address.street,
                'addressCity': db_mailing_address.city,
                'addressRegion': db_mailing_address.region,
                'postalCode': db_mailing_address.postal_code,
                'addressCountry': db_mailing_address.country,
                'deliveryInstructions': db_mailing_address.delivery_instructions,
                'streetAddressAdditional': db_mailing_address.street_additional
            } if db_mailing_address else {}
            new_mailing = {
                'streetAddress': mailing_address.get('streetAddress'),
                'addressCity': mailing_address.get('addressCity'),
                'addressRegion': mailing_address.get('addressRegion'),
                'postalCode': mailing_address.get('postalCode'),
                'addressCountry': mailing_address.get('addressCountry'),
                'deliveryInstructions': mailing_address.get('deliveryInstructions'),
                'streetAddressAdditional': mailing_address.get('streetAddressAdditional')
            }

            if not is_address_changed(old_mailing, new_mailing):
                changes['address'] = {'old': old_mailing, 'new': new_mailing}

            # Delivery address comparison
            db_delivery_address = (Address.find_by_id(matched_db_party.delivery_address_id)
                                  if matched_db_party.delivery_address_id else None)
            
            old_delivery = {
                'streetAddress': db_delivery_address.street,
                'addressCity': db_delivery_address.city,
                'addressRegion': db_delivery_address.region,
                'postalCode': db_delivery_address.postal_code,
                'addressCountry': db_delivery_address.country,
                'deliveryInstructions': db_delivery_address.delivery_instructions,
                'streetAddressAdditional': db_delivery_address.street_additional
            } if db_delivery_address else {}
            new_delivery = {
                'streetAddress': delivery_address.get('streetAddress'),
                'addressCity': delivery_address.get('addressCity'),
                'addressRegion': delivery_address.get('addressRegion'),
                'postalCode': delivery_address.get('postalCode'),
                'addressCountry': delivery_address.get('addressCountry'),
                'deliveryInstructions': delivery_address.get('deliveryInstructions'),
                'streetAddressAdditional': delivery_address.get('streetAddressAdditional')
            }

            if not is_address_changed(old_delivery, new_delivery):
                changes['deliveryAddress'] = {'old': old_delivery, 'new': new_delivery}

            if changes:
                updated_keys.append({
                    'name_changed':changes.get('name', {}).get('changed', False),
                    'email_changed': 'email' in changes,
                    'address_changed': 'address' in changes,
                    'delivery_address_changed': 'deliveryAddress' in changes
                })

    return updated_keys

def normalize_str(value: str) -> str:
   """Convert None or empty values to a stripped uppercase string."""
   return (value or '').strip().upper()
   
def is_same_str(str1: str, str2: str) -> bool:
   """Check if two strings are the same after normalization."""
   return normalize_str(str1) == normalize_str(str2)

def is_name_changed(name1: dict, name2: dict) -> bool:
   """Check if two names are different."""
   name_keys = ['firstName', 'middleName', 'lastName', 'organizationName']
   for key in name_keys:
       if not is_same_str(name1.get(key), name2.get(key)):
           return True
   return False

def is_address_changed(addr1: dict, addr2: dict) -> bool:
   """Check if two addresses are the same."""
   keys = [
       'streetAddress', 'addressCity', 'addressRegion',
       'postalCode', 'addressCountry',
       'deliveryInstructions', 'streetAddressAdditional'
   ]
   for key in keys:
       if not is_same_str(addr1.get(key), addr2.get(key)):
           return False
   return True

def validate_staff_payment(filing_json: dict) -> bool:
    """Check staff specific headers are in the filing."""
    header = filing_json['filing']['header']
    if (
        'routingSlipNumber' in header or
        'bcolAccountNumber' in header or
        'datNumber' in header or
        'waiveFees' in header or
        'priority' in header
    ):
        return True
    return False

def validate_certify_name(filing_json) -> bool:
    """Check certify_by is modified."""
    certify_name = filing_json['filing']['header'].get('certifiedBy')
    try:
        name = g.jwt_oidc_token_info.get('name')
        if certify_name and certify_name == name:
            return False
    except (AttributeError, RuntimeError) as err:
        current_app.logger.error('No JWT present to validate certify name against.')
        current_app.logger.error(err)
        return True
    return True

def validate_certified_by(filing_json: dict) -> list:
    """Validate certifiedBy field."""
    msg = []
    certified_by = filing_json.get('filing', {}).get('header', {}).get('certifiedBy')

    if certified_by not in (None, ""):
        trimmed = get_clean_str(certified_by)
        filing_json['filing']['header']['certifiedBy'] = trimmed

        if not trimmed:
            msg.append({
                'error': 'Certified By field cannot be only whitespace.',
                'path': '/filing/header/certifiedBy'
            })

    return msg

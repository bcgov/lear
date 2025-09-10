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
"""Common validation entry point for all filing submissions."""
from http import HTTPStatus
from typing import Dict

from flask_babel import _ as babel  # noqa: N813

from legal_api.errors import Error
from legal_api.models import Business, Filing
from legal_api.services.filings.validations.common_validations import validate_certify_name, validate_staff_payment
from legal_api.services.permissions import ListActionsPermissionsAllowed, PermissionService
from legal_api.services.utils import get_str

from .admin_freeze import validate as admin_freeze_validate
from .agm_extension import validate as agm_extension_validate
from .agm_location_change import validate as agm_location_change_validate
from .alteration import validate as alteration_validate
from .amalgamation_application import validate as amalgamation_application_validate
from .amalgamation_out import validate as amalgamation_out_validate
from .annual_report import validate as annual_report_validate
from .appoint_receiver import validate as appoint_receiver_validate
from .cease_receiver import validate as cease_receiver_validate
from .change_of_address import validate as coa_validate
from .change_of_directors import validate as cod_validate
from .change_of_name import validate as con_validate
from .change_of_officers import validate as coo_validate
from .change_of_registration import validate as change_of_registration_validate
from .consent_amalgamation_out import validate as consent_amalgamation_out_validate
from .consent_continuation_out import validate as consent_continuation_out_validate
from .continuation_in import validate as continuation_in_validate
from .continuation_out import validate as continuation_out_validate
from .conversion import validate as conversion_validate
from .correction import validate as correction_validate
from .court_order import validate as court_order_validate
from .dissolution import DissolutionTypes
from .dissolution import validate as dissolution_validate
from .incorporation_application import validate as incorporation_application_validate
from .intent_to_liquidate import validate as intent_to_liquidate_validate
from .notice_of_withdrawal import validate as notice_of_withdrawal_validate
from .put_back_off import validate as put_back_off_validate
from .put_back_on import validate as put_back_on_validate
from .registrars_notation import validate as registrars_notation_validate
from .registrars_order import validate as registrars_order_validate
from .registration import validate as registration_validate
from .restoration import validate as restoration_validate
from .schemas import validate_against_schema
from .special_resolution import validate as special_resolution_validate
from .transparency_register import validate as transparency_register_validate


def validate(business: Business,  # pylint: disable=too-many-branches,too-many-statements
             filing_json: Dict,
             account_id=None) -> Error:
    """Validate the filing JSON."""
    err = validate_against_schema(filing_json)
    if err:
        return err

    err = None
    if not validate_staff_payment(filing_json):
        required_permission = ListActionsPermissionsAllowed.STAFF_PAYMENT.value
        message = f'Permission Denied - You do not have permissions to add a staff payment in this filing.'
        error = PermissionService.check_user_permission(required_permission, message)
        if error:
            return error

    if not validate_certify_name(filing_json):
        required_permission = ListActionsPermissionsAllowed.EDITABLE_CERTIFY_NAME.value
        message = f'Permission Denied - You do not have permissions to change certified by in this filing.'
        error = PermissionService.check_user_permission(required_permission, message)
        if error:
            return error
    # check if this is a correction - if yes, ignore all other filing types in the filing since they will be validated
    # differently in a future version of corrections
    if 'correction' in filing_json['filing'].keys():
        err = correction_validate(business, filing_json)
        if err:
            return err

    elif 'dissolution' in filing_json['filing'].keys() \
            and (dissolution_type := filing_json['filing']['dissolution'].get('dissolutionType', None)) \
            and (dissolution_type in ['voluntary', 'administrative']):
        err = dissolution_validate(business, filing_json)
        if err:
            return err

        dissolution_type = get_str(filing_json, '/filing/dissolution/dissolutionType')

        if (business.legal_type == Business.LegalTypes.COOP.value and
                dissolution_type != DissolutionTypes.ADMINISTRATIVE):
            if 'specialResolution' in filing_json['filing'].keys():
                err = special_resolution_validate(business, filing_json)
            else:
                err = Error(HTTPStatus.BAD_REQUEST, [{'error': babel('Special Resolution is required.'),
                                                      'path': '/filing/specialResolution'}])
        if err:
            return err
    elif ('specialResolution' in filing_json['filing'].keys() and
          business.legal_type in [Business.LegalTypes.COOP.value]):
        err = special_resolution_validate(business, filing_json)
        if err:
            return err

        either_con_or_alteration_flag = False

        if 'changeOfName' in filing_json['filing'].keys():
            either_con_or_alteration_flag = True
            err = con_validate(business, filing_json)
        if 'alteration' in filing_json['filing'].keys():
            either_con_or_alteration_flag = True
            err = alteration_validate(business, filing_json)

        if err:
            return err

        if not either_con_or_alteration_flag:
            return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('Either Change of Name or Alteration is required.'),
                                                  'path': '/filing'}])
    else:
        for k in filing_json['filing'].keys():
            # Check if the JSON key exists in the FILINGS reference Dictionary
            if Filing.FILINGS.get(k, None):
                # The type of this Filing exists in the JSON, determine which
                # one it is (Annual Report, Change of Address, or Change of Directors)
                # and validate against the appropriate logic

                if k == Filing.FILINGS['annualReport'].get('name'):
                    err = annual_report_validate(business, filing_json)

                elif k == Filing.FILINGS['changeOfAddress'].get('name'):
                    err = coa_validate(business, filing_json)

                elif k == Filing.FILINGS['changeOfDirectors'].get('name'):
                    err = cod_validate(business, filing_json)

                elif k == Filing.FILINGS['changeOfName'].get('name'):
                    err = con_validate(business, filing_json)

                elif k == Filing.FILINGS['changeOfOfficers'].get('name'):
                    err = coo_validate(business, filing_json)

                elif k == Filing.FILINGS['dissolution'].get('name'):
                    err = dissolution_validate(business, filing_json)

                elif k == Filing.FILINGS['specialResolution'].get('name'):
                    err = special_resolution_validate(business, filing_json)

                elif k == Filing.FILINGS['incorporationApplication'].get('name'):
                    err = incorporation_application_validate(filing_json)

                elif k == Filing.FILINGS['alteration'].get('name'):
                    err = alteration_validate(business, filing_json)

                elif k == Filing.FILINGS['courtOrder'].get('name'):
                    err = court_order_validate(business, filing_json)

                elif k == Filing.FILINGS['registrarsNotation'].get('name'):
                    err = registrars_notation_validate(business, filing_json)

                elif k == Filing.FILINGS['registrarsOrder'].get('name'):
                    err = registrars_order_validate(business, filing_json)

                elif k == Filing.FILINGS['registration'].get('name'):
                    err = registration_validate(filing_json)

                elif k == Filing.FILINGS['changeOfRegistration'].get('name'):
                    err = change_of_registration_validate(business, filing_json)

                elif k == Filing.FILINGS['putBackOn'].get('name'):
                    err = put_back_on_validate(business, filing_json)

                elif k == Filing.FILINGS['adminFreeze'].get('name'):
                    err = admin_freeze_validate(business, filing_json)

                elif k == Filing.FILINGS['conversion'].get('name'):
                    err = conversion_validate(business, filing_json)

                elif k == Filing.FILINGS['restoration'].get('name'):
                    err = restoration_validate(business, filing_json)

                elif k == Filing.FILINGS['consentAmalgamationOut'].get('name'):
                    err = consent_amalgamation_out_validate(business, filing_json)

                elif k == Filing.FILINGS['amalgamationOut'].get('name'):
                    err = amalgamation_out_validate(business, filing_json)

                elif k == Filing.FILINGS['consentContinuationOut'].get('name'):
                    err = consent_continuation_out_validate(business, filing_json)

                elif k == Filing.FILINGS['continuationOut'].get('name'):
                    err = continuation_out_validate(business, filing_json)

                elif k == Filing.FILINGS['agmLocationChange'].get('name'):
                    err = agm_location_change_validate(business, filing_json)

                elif k == Filing.FILINGS['agmExtension'].get('name'):
                    err = agm_extension_validate(business, filing_json)

                elif k == Filing.FILINGS['amalgamationApplication'].get('name'):
                    err = amalgamation_application_validate(filing_json, account_id)

                elif k == Filing.FILINGS['continuationIn'].get('name'):
                    err = continuation_in_validate(filing_json)

                elif k == Filing.FILINGS['intentToLiquidate'].get('name'):
                    err = intent_to_liquidate_validate(business, filing_json)

                elif k == Filing.FILINGS['noticeOfWithdrawal'].get('name'):
                    err = notice_of_withdrawal_validate(filing_json)

                elif k == Filing.FILINGS['putBackOff'].get('name'):
                    err = put_back_off_validate(business, filing_json)

                elif k == Filing.FILINGS['transparencyRegister'].get('name'):
                    err = transparency_register_validate(filing_json)  # pylint: disable=assignment-from-none

                elif k == Filing.FILINGS['appointReceiver'].get('name'):
                    err = appoint_receiver_validate(filing_json)  # pylint: disable=assignment-from-none

                elif k == Filing.FILINGS['ceaseReceiver'].get('name'):
                    err = cease_receiver_validate(business, filing_json)  # pylint: disable=assignment-from-none

                if err:
                    return err

    return None

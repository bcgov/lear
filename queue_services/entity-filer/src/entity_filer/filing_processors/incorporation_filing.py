# Copyright © 2020 Province of British Columbia
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
"""File processing rules and actions for the incorporation of a business."""
import copy
from contextlib import suppress
from http import HTTPStatus
from typing import Dict

import requests
import sentry_sdk
from entity_queue_common.service_utils import QueueException
from flask import current_app
from legal_api.core import BusinessIdentifier, BusinessType
from legal_api.models import Business, Document, Filing, RegistrationBootstrap
from legal_api.models.document import DocumentType
from legal_api.services.bootstrap import AccountService
from legal_api.services.minio import MinioService

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import aliases, business_info, business_profile, shares
from entity_filer.filing_processors.filing_components.offices import update_offices
from entity_filer.filing_processors.filing_components.parties import update_parties
from entity_filer.utils import replace_file_with_certified_copy


def get_next_corp_num(legal_type: str):
    """Retrieve the next available sequential corp-num from COLIN."""
    # this gets called if the new services are generating the Business.identifier.
    if legal_type in BusinessType:
        if business_type := BusinessType.get_enum_by_value(legal_type):
            return BusinessIdentifier.next_identifier(business_type)
        return None

    # legacy Business.Identifier generation
    try:
        # TODO: update this to grab the legal 'class' after legal classes have been defined in lear
        if legal_type == Business.LegalTypes.BCOMP.value:
            business_type = 'BC'
        else:
            business_type = legal_type
        resp = requests.post(f'{current_app.config["COLIN_API"]}/{business_type}')
    except requests.exceptions.ConnectionError:
        current_app.logger.error(f'Failed to connect to {current_app.config["COLIN_API"]}')
        return None

    if resp.status_code == 200:
        new_corpnum = int(resp.json()['corpNum'])
        if new_corpnum and new_corpnum <= 9999999:
            # TODO: Fix endpoint
            return f'{business_type}{new_corpnum:07d}'
    return None


def update_affiliation(business: Business, filing: Filing):
    """Create an affiliation for the business and remove the bootstrap."""
    try:
        bootstrap = RegistrationBootstrap.find_by_identifier(filing.temp_reg)

        rv = AccountService.create_affiliation(
            account=bootstrap.account,
            business_registration=business.identifier,
            business_name=business.legal_name,
            corp_type_code=business.legal_type
        )

        if rv not in (HTTPStatus.OK, HTTPStatus.CREATED):
            deaffiliation = AccountService.delete_affiliation(bootstrap.account, business.identifier)
            sentry_sdk.capture_message(
                f'Queue Error: Unable to affiliate business:{business.identifier} for filing:{filing.id}',
                level='error'
            )
        else:
            # flip the registration
            # recreate the bootstrap, but point to the new business in the name
            old_bs_affiliation = AccountService.delete_affiliation(bootstrap.account, bootstrap.identifier)
            new_bs_affiliation = AccountService.create_affiliation(
                account=bootstrap.account,
                business_registration=bootstrap.identifier,
                business_name=business.identifier,
                corp_type_code='TMP'
            )
            reaffiliate = bool(new_bs_affiliation in (HTTPStatus.OK, HTTPStatus.CREATED)
                               and old_bs_affiliation == HTTPStatus.OK)

        if rv not in (HTTPStatus.OK, HTTPStatus.CREATED) \
                or ('deaffiliation' in locals() and deaffiliation != HTTPStatus.OK)\
                or ('reaffiliate' in locals() and not reaffiliate):
            raise QueueException
    except Exception as err:  # pylint: disable=broad-except; note out any exception, but don't fail the call
        sentry_sdk.capture_message(
            f'Queue Error: Affiliation error for filing:{filing.id}, with err:{err}',
            level='error'
        )


def _update_cooperative(incorp_filing: Dict, business: Business, filing: Filing):
    cooperative_obj = incorp_filing.get('cooperative', None)
    if cooperative_obj:
        # create certified copy for rules document
        rules_file_key = cooperative_obj.get('rulesFileKey')
        rules_file = MinioService.get_file(rules_file_key)
        rules_file_name = cooperative_obj.get('rulesFileName')
        replace_file_with_certified_copy(rules_file.data, business, rules_file_key, business.founding_date)

        business.association_type = cooperative_obj.get('cooperativeAssociationType')
        document = Document()
        document.type = DocumentType.COOP_RULES.value
        document.file_key = rules_file_key
        document.file_name = rules_file_name
        document.content_type = document.file_name.split('.')[-1]
        document.business_id = business.id
        document.filing_id = filing.id
        business.documents.append(document)

        # create certified copy for memorandum document
        memorandum_file_key = cooperative_obj.get('memorandumFileKey')
        memorandum_file = MinioService.get_file(memorandum_file_key)
        memorandum_file_name = cooperative_obj.get('memorandumFileName')
        replace_file_with_certified_copy(memorandum_file.data, business, memorandum_file_key, business.founding_date)

        document = Document()
        document.type = DocumentType.COOP_MEMORANDUM.value
        document.file_key = memorandum_file_key
        document.file_name = memorandum_file_name
        document.content_type = document.file_name.split('.')[-1]
        document.business_id = business.id
        document.filing_id = filing.id
        business.documents.append(document)

    return business


def process(business: Business,  # pylint: disable=too-many-branches
            filing: Dict,
            filing_rec: Filing,
            filing_meta: FilingMeta):  # pylint: disable=too-many-branches
    """Process the incoming incorporation filing."""
    # Extract the filing information for incorporation
    incorp_filing = filing.get('filing', {}).get('incorporationApplication')
    is_correction = filing_rec.filing_type == 'correction'
    filing_meta.incorporation_application = {}

    if not incorp_filing:
        raise QueueException(f'IA legal_filing:incorporationApplication missing from {filing_rec.id}')
    if business and not is_correction:
        raise QueueException(f'Business Already Exist: IA legal_filing:incorporationApplication {filing_rec.id}')

    business_info_obj = incorp_filing.get('nameRequest')

    if is_correction:
        business_info.set_legal_name(business.identifier, business, business_info_obj)
        if legal_name := business_info_obj.get('legalName', None):
            filing_meta.correction = {**filing_meta.correction,
                                      **{'fromLegalName': business.legal_name,
                                         'toLegalName': legal_name}}
    else:

        if filing_rec.colin_event_ids:
            corp_num = filing['filing']['business']['identifier']

        else:
            # Reserve the Corp Number for this entity
            corp_num = get_next_corp_num(business_info_obj['legalType'])
            if not corp_num:
                raise QueueException(
                    f'incorporationApplication {filing_rec.id} unable to get a business registration number.')

        # Initial insert of the business record
        business = Business()
        business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
        business = _update_cooperative(incorp_filing, business, filing_rec)
        business.state = Business.State.ACTIVE

        if nr_number := business_info_obj.get('nrNumber', None):
            filing_meta.incorporation_application = {**filing_meta.incorporation_application,
                                                     **{'nrNumber': nr_number,
                                                        'legalName': business_info_obj.get('legalName', None)}}

        if not business:
            raise QueueException(f'IA incorporationApplication {filing_rec.id}, Unable to create business.')

    if offices := incorp_filing['offices']:
        update_offices(business, offices)

    if parties := incorp_filing.get('parties'):
        update_parties(business, parties, filing_rec)

    if share_structure := incorp_filing.get('shareStructure'):
        shares.update_share_structure(business, share_structure)

    if name_translations := incorp_filing.get('nameTranslations'):
        aliases.update_aliases(business, name_translations)

    if not is_correction and not filing_rec.colin_event_ids:
        # Update the filing json with identifier and founding date.
        ia_json = copy.deepcopy(filing_rec.filing_json)
        if not ia_json['filing'].get('business'):
            ia_json['filing']['business'] = {}
        ia_json['filing']['business']['identifier'] = business.identifier
        ia_json['filing']['business']['foundingDate'] = business.founding_date.isoformat()
        filing_rec._filing_json = ia_json  # pylint: disable=protected-access; bypass to update filing data
    return business, filing_rec, filing_meta


def post_process(business: Business, filing: Filing):
    """Post processing activities for incorporations.

    THIS SHOULD NOT ALTER THE MODEL
    """
    with suppress(IndexError, KeyError, TypeError):
        if err := business_profile.update_business_profile(
            business,
            filing.json['filing']['incorporationApplication']['contactPoint']
        ):
            sentry_sdk.capture_message(
                f'Queue Error: Update Business for filing:{filing.id}, error:{err}',
                level='error')

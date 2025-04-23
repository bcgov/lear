# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""File processing rules and actions for historic conversion filing.

A conversion filing is for a business that was created before COLIN,
the original system to manage business corporations.

As the business exists, no new registration identifiers, names, or structures are
altered.

There are no corrections for a conversion filing.
"""
# pylint: disable=superfluous-parens; as pylance requires it
from contextlib import suppress
from typing import Dict

import dpath
from business_filer.exceptions import QueueException
from business_model.models import Business, Filing
from business_filer.common.legislation_datetime import LegislationDatetime

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.change_of_registration import update_parties as upsert_parties
from business_filer.filing_processors.filing_components import aliases, business_info, shares
from business_filer.filing_processors.filing_components.offices import update_offices
from business_filer.filing_processors.filing_components.parties import update_parties


def process(business: Business,  # pylint: disable=too-many-branches
            filing: Dict,
            filing_rec: Filing,
            filing_meta: FilingMeta):  # pylint: disable=too-many-branches
    """Process the incoming historic conversion filing."""
    # Extract the filing information for incorporation
    filing_meta.conversion = {}
    if not (conversion_filing := filing.get('filing', {}).get('conversion')):
        raise QueueException(f'CONVL legal_filing:conversion missing from {filing_rec.id}')
    if business and business.legal_type in ['SP', 'GP']:
        _process_firms_conversion(business, filing, filing_rec, filing_meta)
    else:
        business = _process_corps_conversion(business, conversion_filing, filing, filing_rec)

    return business, filing_rec


def _process_corps_conversion(business, conversion_filing, filing, filing_rec):
    if business:
        raise QueueException(f'Business Already Exist: CONVL legal_filing:conversion {filing_rec.id}')
    if not (corp_num := filing.get('filing', {}).get('business', {}).get('identifier')):
        raise QueueException(f'conversion {filing_rec.id} missing the business identifier.')
    # Initial insert of the business record
    business_info_obj = conversion_filing.get('nameRequest')
    if not (business := business_info.update_business_info(corp_num, Business(), business_info_obj, filing_rec)):
        raise QueueException(f'CONVL conversion {filing_rec.id}, Unable to create business.')
    if offices := conversion_filing.get('offices'):
        update_offices(business, offices)
    if parties := conversion_filing.get('parties'):
        update_parties(business, parties, filing_rec)
    if share_structure := conversion_filing.get('shareStructure'):
        shares.update_share_structure(business, share_structure)
    if name_translations := conversion_filing.get('nameTranslations'):
        aliases.update_aliases(business, name_translations)
    return business


def _process_firms_conversion(business: Business, conversion_filing: Dict, filing_rec: Filing, filing_meta: FilingMeta):
    # Name change if present
    with suppress(IndexError, KeyError, TypeError):
        name_request_json = dpath.get(conversion_filing, '/filing/conversion/nameRequest')
        if name_request_json.get('legalName'):
            from_legal_name = business.legal_name
            business_info.set_legal_name(business.identifier, business, name_request_json)
            if from_legal_name != business.legal_name:
                filing_meta.conversion = {**filing_meta.conversion, **{'fromLegalName': from_legal_name,
                                                                       'toLegalName': business.legal_name}}
    # Update Nature of Business
    if (naics := conversion_filing.get('filing', {}).get('conversion', {}).get('business', {}).get('naics')) and \
            naics.get('naicsDescription'):
        business_info.update_naics_info(business, naics)
        filing_meta.conversion = {**filing_meta.conversion, **{'naicsDescription': naics.get('naicsDescription')}}

    # Update business office if present
    with suppress(IndexError, KeyError, TypeError):
        offices_json = dpath.get(conversion_filing, '/filing/conversion/offices')
        update_offices(business, offices_json)

    # Update parties
    with suppress(IndexError, KeyError, TypeError):
        party_json = dpath.get(conversion_filing, '/filing/conversion/parties')
        upsert_parties(business, party_json, filing_rec)

    # update business start date, if any is present
    with suppress(IndexError, KeyError, TypeError):
        business_start_date = dpath.get(conversion_filing, '/filing/conversion/startDate')
        if business_start_date:
            business.start_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(business_start_date)

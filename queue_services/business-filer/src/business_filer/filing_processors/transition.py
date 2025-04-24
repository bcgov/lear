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
"""File processing rules and actions for the transition of a business."""

from business_model.models import Business, Filing

from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import aliases, shares
from business_filer.filing_processors.filing_components.offices import update_offices
from business_filer.filing_processors.filing_components.parties import update_parties


def process(business: Business, filing_rec: Filing, filing: dict, filing_meta: FilingMeta):
    # pylint: disable=too-many-locals; 1 extra
    """Process the incoming transition filing."""
    # Extract the filing information for transition application
    if not (transition_filing := filing.get("transition")):  # pylint: disable=superfluous-parens;
        raise QueueException(f"legal_filing:transition data missing from {filing_rec.id}")
    if not business:
        raise QueueException(f"Business does not exist: legal_filing:transitionApplication {filing_rec.id}")

    # Initial insert of the business record
    business.restriction_ind = transition_filing.get("hasProvisions")

    if offices := transition_filing["offices"]:
        update_offices(business, offices)

    if parties := transition_filing.get("parties"):
        update_parties(business, parties, filing_rec)

    if share_structure := transition_filing["shareStructure"]:
        shares.update_share_structure(business, share_structure)

    if name_translations := transition_filing.get("nameTranslations"):
        aliases.update_aliases(business, name_translations)

    return filing_rec

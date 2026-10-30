# Copyright © 2026 Province of British Columbia
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
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Person name rendering tests for the template parts that print LASTNAME, FIRSTNAME."""
import re

import pytest

from tests.unit.reports.templates import get_template

ADDRESS = {
    "streetAddress": "123 Main St",
    "streetAddressAdditional": "",
    "addressCity": "Victoria",
    "addressRegion": "BC",
    "postalCode": "V8V 1V1",
    "addressCountry": "CA",
    "addressCountryDescription": "Canada",
}


def _person(last_name, first_name="", middle_name="", roles=()):
    return {
        "officer": {
            "partyType": "person",
            "lastName": last_name,
            "firstName": first_name,
            "middleName": middle_name,
            "middleInitial": middle_name[:1],
        },
        "role": "director",
        "roles": [{"roleType": role, "appointmentDate": "2026-01-01"} for role in roles],
        "mailingAddress": dict(ADDRESS),
        "deliveryAddress": dict(ADDRESS),
    }


def _people(*roles):
    return [_person("SMITH", "JOHN", "ANDREW", roles), _person("ONLYLAST", roles=roles)]


def _text(rendered):
    """Return the visible text the way a browser would: tags removed, whitespace runs collapsed."""
    return " ".join(re.sub(r"<[^>]+>", "", rendered).split())


LABELS = {
    "labelAdded": lambda: "ADDED",
    "labelCeased": lambda: "CEASED",
    "labelCorrected": lambda: "CORRECTED",
    "labelRemoved": lambda: "REMOVED",
}

# part -> context builder; the builder gets the list of people to print
PARTS = {
    "/template-parts/directors.html": lambda p: {
        "listOfDirectors": {"directorsAppointed": p, "directorsCeased": p, "directors": p}},
    "/template-parts/common/directors.html": lambda p: {"parties": _people("Director")},
    "/template-parts/correction/directors.html": lambda p: {
        "parties": _people("Director"), "partyChange": True, "effective_date": "January 1, 2026"},
    "/template-parts/notice-of-articles/directors.html": lambda p: {"parties": p, "reportType": "noticeOfArticles"},
    "/template-parts/notice-of-articles/officers.html": lambda p: {"officers": _people("President")},
    "/template-parts/business-summary/parties.html": lambda p: {"parties": _people("Partner")},
    "/template-parts/business-summary/receiverInformation.html": lambda p: {"receivers": _people("Receiver")},
    "/template-parts/business-summary/recordKeeper.html": lambda p: {"custodians": p},
    "/template-parts/change-of-registration/partner.html": lambda p: {
        "parties": _people("Partner"), "newParties": _people("Partner"), "ceasedParties": _people("Partner"),
        "partyChange": True, "header": {"reportType": "changeOfRegistration", "name": "changeOfRegistration"}},
    "/template-parts/change-of-registration/proprietor.html": lambda p: {
        "parties": _people("Proprietor"), "partyChange": True},
    "/template-parts/dissolution/custodianOfRecords.html": lambda p: {"dissolution": {"parties": p}},
    "/template-parts/incorporation-application/completingPartyCoop.html": lambda p: {
        "parties": _people("Completing Party")},
    "/template-parts/incorporation-application/incorporator.html": lambda p: {"parties": _people("Incorporator")},
    "/template-parts/registration-statement/party.html": lambda p: {"parties": _people("Partner")},
    "/template-parts/registration/party.html": lambda p: {
        "registration": {"nameRequest": {"legalType": "GP"}, "parties": _people("Partner")}},
    "/template-parts/restoration-application/applicant.html": lambda p: {"parties": _people("Applicant")},
}

# parts that print a single person
SINGLE_PARTS = {
    "/template-parts/registration-statement/completingParty.html": lambda person: {"completingParty": person},
}


def _render(part, context):
    base = {"business": {"legalType": "BC", "identifier": "BC1234567"}, "header": {}, **LABELS}
    return _text(get_template(part).render(**{**base, **context}))


def _assert_names(text):
    assert "SMITH, JOHN" in text
    assert "SMITH ," not in text
    assert "ONLYLAST" in text
    assert "ONLYLAST," not in text
    assert "ONLYLAST ," not in text


@pytest.mark.parametrize("part", PARTS.keys())
def test_person_name_has_no_space_before_comma(app, part):
    """Assert a person renders as LASTNAME, FIRSTNAME and a last name alone gets no comma."""
    people = _people()
    people[0]["officer"]["id"] = 1
    people[1]["officer"]["id"] = 2

    _assert_names(_render(part, PARTS[part](people)))


@pytest.mark.parametrize("part", SINGLE_PARTS.keys())
def test_single_person_name_has_no_space_before_comma(app, part):
    """Assert the single-person parts render LASTNAME, FIRSTNAME and a last name alone without a comma."""
    text = " ".join(_render(part, SINGLE_PARTS[part](person)) for person in _people())

    _assert_names(text)

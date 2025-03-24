# Copyright © 2022 Province of British Columbia
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

"""Tests to assure the RequestTracker Model.

Test-Suite to ensure that the RequestTracker Model is working as expected.
"""

from business_model.models import RequestTracker

from tests.models import factory_business, factory_filing


def test_valid_request_tracker_save(session):
    """Assert that a valid request_tracker can be saved."""
    identifier = 'FM1234567'
    business = factory_business(identifier)
    request_tracker = RequestTracker(
        business_id=business.id,
        service_name=RequestTracker.ServiceName.BN_HUB,
        request_type=RequestTracker.RequestType.INFORM_CRA,
        request_object=''
    )
    request_tracker.save()
    assert request_tracker.id


sample_xml = """<?xml version="1.0"?>
<SBNCreateProgramAccountRequest>
  <header>
    <requestMode>A</requestMode>
    <documentSubType>000</documentSubType>
    <senderID>CPPR</senderID>
    <receiverID>BCSBNHUB</receiverID>
    <partnerNote>1324909</partnerNote>
    <CCRAHeader>
      <userApplication>BI</userApplication>
      <userRole>01</userRole>
    </CCRAHeader>
  </header>
  <body>
    <businessProgramIdentifier>BC</businessProgramIdentifier>
    <SBNProgramTypeCode>113</SBNProgramTypeCode>
    <businessCore>
      <programAccountTypeCode>01</programAccountTypeCode>
      <crossReferenceProgramNumber>FM1006249</crossReferenceProgramNumber>
      <businessTypeCode>01</businessTypeCode>
      <businessSubTypeCode>01</businessSubTypeCode>
    </businessCore>
    <programAccountStatus>
      <programAccountStatusCode>01</programAccountStatusCode>
      <effectiveDate>2022-03-11</effectiveDate>
    </programAccountStatus>
    <legalName>test test</legalName>
    <operatingName>
      <operatingName>DALLAS/WATERFORD ESTATES INVESTMENTS I LIMITED PARTNERSHIP</operatingName>
      <operatingNamesequenceNumber>1</operatingNamesequenceNumber>
    </operatingName>
    <businessAddress>
      <canadianCivic>
        <civicNumber>222</civicNumber>
        <streetName>GREENLEA</streetName>
        <streetType>PL</streetType>
      </canadianCivic>
      <municipality>VICTORIA</municipality>
      <provinceStateCode>BC</provinceStateCode>
      <postalCode>V8Z6N1</postalCode>
      <countryCode>CA</countryCode>
    </businessAddress>
    <mailingAddress>
      <canadianCivic>
        <civicNumber>222</civicNumber>
        <streetName>GREENLEA</streetName>
        <streetType>PL</streetType>
      </canadianCivic>
      <municipality>VICTORIA</municipality>
      <provinceStateCode>BC</provinceStateCode>
      <postalCode>V8Z6N1</postalCode>
      <countryCode>CA</countryCode>
    </mailingAddress>
    <owner>
      <ownerIndividual>
        <lastName>test</lastName>
        <givenName>test</givenName>
      </ownerIndividual>
    </owner>
    <businessActivityDeclaration>
      <businessActivityDescription>Tourism</businessActivityDescription>
    </businessActivityDeclaration>
  </body>
</SBNCreateProgramAccountRequest>"""


def test_find_request_tracker_by_id(session):
    """Assert that the method returns correct value."""
    identifier = 'FM1234567'
    business = factory_business(identifier)
    request_tracker = RequestTracker(
        business_id=business.id,
        service_name=RequestTracker.ServiceName.BN_HUB,
        request_type=RequestTracker.RequestType.INFORM_CRA,
        request_object=sample_xml
    )
    request_tracker.save()

    res = RequestTracker.find_by_id(request_tracker.id)

    assert res
    assert res.request_object == request_tracker.request_object


def test_find_request_tracker_by(session):
    """Assert that the method returns correct value."""
    identifier = 'FM1234567'
    business = factory_business(identifier)
    filing = factory_filing(business, {'filing': {'header': {'name': 'registration'}}}, filing_type='registration')
    request_tracker = RequestTracker(
        business_id=business.id,
        filing_id=filing.id,
        service_name=RequestTracker.ServiceName.BN_HUB,
        request_type=RequestTracker.RequestType.INFORM_CRA,
        request_object=sample_xml
    )
    request_tracker.save()

    res = RequestTracker.find_by(business.id,
                                 RequestTracker.ServiceName.BN_HUB)
    assert len(res) == 1
    assert res[0].id == request_tracker.id

    res = RequestTracker.find_by(business.id,
                                 RequestTracker.ServiceName.BN_HUB,
                                 RequestTracker.RequestType.INFORM_CRA)
    assert len(res) == 1
    assert res[0].id == request_tracker.id

    res = RequestTracker.find_by(business.id,
                                 RequestTracker.ServiceName.BN_HUB,
                                 RequestTracker.RequestType.INFORM_CRA,
                                 filing_id=filing.id)
    assert len(res) == 1
    assert res[0].id == request_tracker.id

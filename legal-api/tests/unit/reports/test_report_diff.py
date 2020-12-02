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

"""Tests to assure the data has been formatted with diff."""

from legal_api.reports.report import Report


def test_format_with_diff_data(session):
    """Assert that the filing is formatted with diff data."""
    offices = {
        'recordsOffice': {
            'mailingAddress': {'postalCode': 'V8T 3W1', 'addressCity': 'Victoria', 'addressType': 'mailing', 'addressRegion': 'BC', 'streetAddress': '2500 Blackwood St', 'addressCountry': 'Canada', 'deliveryInstructions': '', 'streetAddressAdditional': '', 'addressCountryDescription': 'Canada'},  # noqa: E501;
            'deliveryAddress': {'postalCode': 'V8T 3W1', 'addressCity': 'Victoria', 'addressType': 'delivery', 'addressRegion': 'BC', 'streetAddress': '2500 Blackwood St', 'addressCountry': 'Canada', 'deliveryInstructions': '', 'streetAddressAdditional': '', 'addressCountryDescription': 'Canada'}  # noqa: E501;
        },
        'registeredOffice': {
            'mailingAddress': {'postalCode': 'V8T 3W1', 'addressCity': 'Victoria', 'addressType': 'mailing', 'addressRegion': 'BC', 'streetAddress': '2500 Blackwood St', 'addressCountry': 'Canada', 'deliveryInstructions': '', 'streetAddressAdditional': '', 'addressCountryDescription': 'Canada'},  # noqa: E501;
            'deliveryAddress': {'postalCode': 'V8T 3W1', 'addressCity': 'Victoria', 'addressType': 'delivery', 'addressRegion': 'BC', 'streetAddress': '2500 Blackwood St', 'addressCountry': 'Canada', 'deliveryInstructions': '', 'streetAddressAdditional': '', 'addressCountryDescription': 'Canada'}  # noqa: E501;
        }
    }
    parties = [
        {
            'roles': [{'roleType': 'Incorporator', 'appointmentDate': '2020-11-18'}, {'roleType': 'Director', 'appointmentDate': '2020-11-18'}],  # noqa: E501;
            'officer': {'id': '10633', 'lastName': 'V', 'firstName': 'MV', 'partyType': 'Person'},
            'mailingAddress': {'postalCode': 'V8W 2E7', 'addressCity': 'Victoria', 'addressRegion': 'BC', 'streetAddress': '1207 Douglas St', 'addressCountry': 'Canada', 'deliveryInstructions': '', 'streetAddressAdditional': '', 'addressCountryDescription': 'Canada'},  # noqa: E501;
            'deliveryAddress': {'postalCode': 'V8W 2E7', 'addressCity': 'Victoria', 'addressRegion': 'BC', 'streetAddress': '1207 Douglas St', 'addressCountry': 'Canada', 'deliveryInstructions': '', 'streetAddressAdditional': '', 'addressCountryDescription': 'Canada'}  # noqa: E501;
        },
        {
            'roles': [{'roleType': 'Completing Party', 'appointmentDate': '2020-11-18'}, {'roleType': 'Director', 'appointmentDate': '2020-11-18'}],  # noqa: E501;
            'officer': {'id': '700237d2-9f96-4e9d-9591-55de0951f565', 'email': 'abc@xyz.com', 'orgName': '', 'lastName': 'M', 'firstName': 'MM', 'partyType': 'Person', 'middleName': ''},  # noqa: E501;
            'mailingAddress': {'postalCode': 'V8W 2E7', 'addressCity': 'Victoria', 'addressRegion': 'BC', 'streetAddress': '1207 Douglas St', 'addressCountry': 'Canada', 'streetAddressAdditional': ''},  # noqa: E501;
            'deliveryAddress': {'postalCode': 'V8W 2E7', 'addressCity': 'Victoria', 'addressRegion': 'BC', 'streetAddress': '1207 Douglas St', 'addressCountry': 'Canada', 'streetAddressAdditional': ''}  # noqa: E501;
        }
    ]
    share_classes = [
        {'id': '705', 'name': 'test Shares', 'type': 'Class', 'series': [{'id': '166', 'name': 'sub test Shares', 'type': 'Series', 'priority': 1, 'hasMaximumShares': True, 'maxNumberOfShares': 10, 'hasRightsOrRestrictions': True}, {'id': '167', 'name': 'sub test 1 Shares', 'type': 'Series', 'priority': 2, 'hasMaximumShares': True, 'maxNumberOfShares': 10, 'hasRightsOrRestrictions': False}], 'currency': 'CAD', 'parValue': '5', 'priority': 1, 'hasParValue': True, 'hasMaximumShares': True, 'maxNumberOfShares': 100, 'hasRightsOrRestrictions': True},  # noqa: E501;
        {'id': '706', 'name': 'test1 Shares', 'type': 'Class', 'series': [{'id': '168', 'name': 'second sub test Shares', 'type': 'Series', 'priority': 1, 'hasParValue': False, 'hasMaximumShares': True, 'maxNumberOfShares': '11', 'hasRightsOrRestrictions': False}], 'currency': 'CAD', 'parValue': 10, 'priority': 2, 'hasParValue': True, 'hasMaximumShares': True, 'maxNumberOfShares': 100, 'hasRightsOrRestrictions': True}, {'id': 'cee3d66d-da9f-4892-9f83-9c2551aa46ab', 'name': 'test3 Shares', 'type': 'Class', 'series': [], 'currency': 'CAD', 'parValue': '5', 'priority': 4, 'hasParValue': True, 'hasMaximumShares': True, 'maxNumberOfShares': '123', 'hasRightsOrRestrictions': False}  # noqa: E501;
    ]
    filing = {
        'header': {'date': '2020-11-18', 'name': 'correction', 'priority': False, 'waiveFees': True, 'certifiedBy': 'vys', 'filingId': 111173},  # noqa: E501;
        'business': {'foundingDate': '2020-11-18T19:53:02.307840+00:00', 'identifier': 'BC1230032', 'lastModified': '2020-11-18T23:00:17.547017+00:00', 'lastAnnualReport': '', 'nextAnnualReport': '2021-11-18T19:53:02.307840+00:00', 'lastAnnualGeneralMeetingDate': '', 'lastLedgerTimestamp': '2020-11-18T23:00:17.547033+00:00', 'legalName': '1230032 B.C. LTD.', 'legalType': 'BEN', 'hasRestrictions': False, 'fiscalYearEndDate': '2020-11-18', 'dissolutionDate': None, 'formatted_founding_date_time': 'November 18, 2020 at 11:53 AM Pacific Time', 'formatted_founding_date': 'November 18, 2020'},  # noqa: E501;
        'correction': {
            'comment': 'Correction for Incorporation Application filed on 2020-11-18.\ntest', 'correctedFilingId': 111167, 'correctedFilingDate': '2020-11-18', 'correctedFilingType': 'incorporationApplication',  # noqa: E501;
            'diff': [{'oldValue': 'V8W 2E7', 'newValue': 'V8T 3W1', 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/postalCode'}, {'oldValue': '1207 Douglas St', 'newValue': '2500 Blackwood St', 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/streetAddress'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/deliveryInstructions'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/streetAddressAdditional'}, {'oldValue': 'V8W 2E7', 'newValue': 'V8T 3W1', 'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/postalCode'}, {'oldValue': '1207 Douglas St', 'newValue': '2500 Blackwood St', 'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/streetAddress'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/deliveryInstructions'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/streetAddressAdditional'}, {'oldValue': 'V8W 2E7', 'newValue': 'V8T 3W1', 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/postalCode'}, {'oldValue': '1207 Douglas St', 'newValue': '2500 Blackwood St', 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/streetAddress'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/deliveryInstructions'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/streetAddressAdditional'}, {'oldValue': 'V8W 2E7', 'newValue': 'V8T 3W1', 'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/postalCode'}, {'oldValue': '1207 Douglas St', 'newValue': '2500 Blackwood St', 'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/streetAddress'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/deliveryInstructions'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/streetAddressAdditional'}, {'oldValue': 'M', 'newValue': 'V', 'path': '/filing/incorporationApplication/parties/10633/officer/lastName'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/parties/10633/mailingAddress/deliveryInstructions'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/parties/10633/mailingAddress/streetAddressAdditional'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/parties/10633/deliveryAddress/deliveryInstructions'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/parties/10633/deliveryAddress/streetAddressAdditional'}, {'oldValue': None, 'newValue': {'roles': [{'roleType': 'Completing Party', 'appointmentDate': '2020-11-18'}, {'roleType': 'Director', 'appointmentDate': '2020-11-18'}], 'officer': {'id': '700237d2-9f96-4e9d-9591-55de0951f565', 'email': 'abc@xyz.com', 'orgName': '', 'lastName': 'M', 'firstName': 'MM', 'partyType': 'Person', 'middleName': ''}, 'mailingAddress': {'postalCode': 'V8W 2E7', 'addressCity': 'Victoria', 'addressRegion': 'BC', 'streetAddress': '1207 Douglas St', 'addressCountry': 'CA', 'streetAddressAdditional': ''}, 'deliveryAddress': {'postalCode': 'V8W 2E7', 'addressCity': 'Victoria', 'addressRegion': 'BC', 'streetAddress': '1207 Douglas St', 'addressCountry': 'CA', 'streetAddressAdditional': ''}, 'id': '700237d2-9f96-4e9d-9591-55de0951f565'}, 'path': '/filing/incorporationApplication/parties'}, {'oldValue': {'officer': {'firstName': 'VM', 'lastName': 'V', 'partyType': 'Person', 'id': '10632', 'email': 'abc@xyz.com'}, 'deliveryAddress': {'streetAddress': '1207 Douglas St', 'streetAddressAdditional': '', 'addressCity': 'Victoria', 'addressRegion': 'BC', 'addressCountry': 'CA', 'addressCountryDescription': 'Canada', 'postalCode': 'V8W 2E7', 'deliveryInstructions': ''}, 'mailingAddress': {'streetAddress': '1207 Douglas St', 'streetAddressAdditional': '', 'addressCity': 'Victoria', 'addressRegion': 'BC', 'addressCountry': 'CA', 'addressCountryDescription': 'Canada', 'postalCode': 'V8W 2E7', 'deliveryInstructions': ''}, 'id': '10632', 'roles': [{'appointmentDate': '2020-11-18', 'roleType': 'Completing Party'}, {'appointmentDate': '2020-11-18', 'roleType': 'Incorporator'}, {'appointmentDate': '2020-11-18', 'roleType': 'Director'}]}, 'newValue': None, 'path': '/filing/incorporationApplication/parties'}, {'oldValue': None, 'newValue': '', 'path': '/filing/incorporationApplication/contactPoint/extension'}, {'oldValue': None, 'newValue': False, 'path': '/filing/incorporationApplication/shareStructure/shareClasses/705/series/167/hasRightsOrRestrictions'}, {'oldValue': 10.0, 'newValue': '5', 'path': '/filing/incorporationApplication/shareStructure/shareClasses/705/parValue'}, {'oldValue': None, 'newValue': False, 'path': '/filing/incorporationApplication/shareStructure/shareClasses/706/series/168/hasParValue'}, {'oldValue': 10, 'newValue': '11', 'path': '/filing/incorporationApplication/shareStructure/shareClasses/706/series/168/maxNumberOfShares'}, {'oldValue': None, 'newValue': False, 'path': '/filing/incorporationApplication/shareStructure/shareClasses/706/series/168/hasRightsOrRestrictions'}, {'oldValue': {'id': '169', 'name': 'second sub test 1 Shares', 'priority': 2, 'hasMaximumShares': True, 'maxNumberOfShares': 10, 'hasRightsOrRestrictions': False, 'type': 'Series'}, 'newValue': None, 'path': '/filing/incorporationApplication/shareStructure/shareClasses/706/series'}, {'oldValue': None, 'newValue': {'id': 'cee3d66d-da9f-4892-9f83-9c2551aa46ab', 'name': 'test3 Shares', 'type': 'Class', 'series': [], 'currency': 'CAD', 'parValue': '5', 'priority': 4, 'hasParValue': True, 'hasMaximumShares': True, 'maxNumberOfShares': '123', 'hasRightsOrRestrictions': False}, 'path': '/filing/incorporationApplication/shareStructure/shareClasses'}, {'oldValue': {'id': '707', 'name': 'test2 Shares', 'priority': 3, 'hasMaximumShares': True, 'maxNumberOfShares': 100, 'hasParValue': False, 'parValue': None, 'currency': None, 'hasRightsOrRestrictions': False, 'series': [], 'type': 'Class'}, 'newValue': None, 'path': '/filing/incorporationApplication/shareStructure/shareClasses'}, {'oldValue': None, 'newValue': 'TEST_D', 'path': '/filing/incorporationApplication/nameTranslations'}, {'oldValue': 'TEST_B', 'newValue': None, 'path': '/filing/incorporationApplication/nameTranslations'}, {'oldValue': 'TEST_A', 'newValue': 'TEST_C', 'path': '/filing/incorporationApplication/nameTranslations'}]},  # noqa: E501;
        'incorporationApplication': {
            'offices': offices,
            'parties': parties,
            'nameRequest': {'legalType': 'BEN'},
            'contactPoint': {'email': 'no@reply.com', 'phone': '(555) 555-5555', 'extension': ''},
            'shareStructure': {
                'shareClasses': share_classes
            },
            'nameTranslations': [{'name': 'test_d'}, {'id': 1, 'name': 'TEST_C'}],  # noqa: E501;
            'incorporationAgreement': {'agreementType': 'sample'}},
        'listOfTranslations': ['test_d'],
        'offices': offices,
        'parties': parties,
        'shareClasses': share_classes
    }
    Report(filing)._format_with_diff_data(filing)

    assert filing['hasNameTranslationsCorrected']

    offices = filing['offices']
    assert offices['registeredOffice']['mailingAddress']['hasCorrected']
    assert offices['registeredOffice']['deliveryAddress']['hasCorrected']
    assert offices['recordsOffice']['mailingAddress']['hasCorrected']
    assert offices['recordsOffice']['deliveryAddress']['hasCorrected']

    parties = filing['parties']
    party_10633 = next((x for x in parties if x['officer']['id'] == '10633'), {})
    assert party_10633['hasCorrected']
    party_10632 = next((x for x in parties if x['officer']['id'] == '10632'), {})
    assert party_10632['hasRemoved']

    share_classes = filing['shareClasses']
    share_class_705 = next((x for x in share_classes if x['id'] == '705'), {})
    assert share_class_705['hasCorrected']
    share_class_707 = next((x for x in share_classes if x['id'] == '707'), {})
    assert share_class_707['hasRemoved']

    share_series_167 = next((x for x in share_class_705.get('series', []) if x['id'] == '167'), {})
    assert share_series_167['hasCorrected']

    share_class_706 = next((x for x in share_classes if x['id'] == '706'), {})
    share_series_168 = next((x for x in share_class_706.get('series', []) if x['id'] == '168'), {})
    assert share_series_168['hasCorrected']
    share_series_169 = next((x for x in share_class_706.get('series', []) if x['id'] == '169'), {})
    assert share_series_169['hasRemoved']

    # Test without diff
    filing['correction']['diff'] = []
    Report(filing)._format_with_diff_data(filing)

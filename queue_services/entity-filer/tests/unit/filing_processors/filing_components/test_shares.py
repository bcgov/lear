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
"""The Unit Tests for the business filing component processors."""
import pytest
from legal_api.models import Business
from sql_versioning import version_class

from entity_filer.filing_processors.filing_components import shares
from tests import strip_keys_from_dict


@pytest.mark.parametrize('test_name,resolution_dates,expected_error', [
    ('valid resolution_dates', [], None),
    ('valid resolution_dates', ['2020-05-23'], None),
    ('valid resolution_dates', ['2020-05-23', '2020-06-01'], None),
    ('invalid resolution_dates', ['2020-05-23', 'error'],
     [{'error_code': 'FILER_INVALID_RESOLUTION_DATE', 'error_message': "Filer: invalid resolution date:'error'"}])
])
def test_manage_share_structure__resolution_dates(
        app, session,
        test_name, resolution_dates, expected_error):
    """Assert that the corp share resolution date gets set."""
    new_data = {'shareStructure': {
        'resolutionDates': resolution_dates
    }}

    business = Business()
    business.save()
    err = shares.update_share_structure(business, new_data['shareStructure'])
    business.save()

    check_business = Business.find_by_internal_id(business.id)
    check_resolution = check_business.resolutions.all()

    if err:
        assert err == expected_error
    else:
        assert len(check_resolution) == len(resolution_dates)
        assert set(resolution_dates) == \
            set([x.resolution_date.isoformat() for x in check_resolution])


SINGLE_SHARE_CLASS = {
    'shareStructure': {
        'shareClasses': [{
            'name': 'class1',
            'priority': 1,
            'maxNumberOfShares': 600,
            'parValue': 1,
            'currency': 'CAD',
            'hasMaximumShares': True,
            'hasParValue': True,
            'hasRightsOrRestrictions': False,
            'series': [{
                    'name': 'series1',
                    'priority': 1,
                    'maxNumberOfShares': 600,
                    'hasMaximumShares': True,
                    'hasRightsOrRestrictions': False
            }]
        }]
    },
}


@pytest.mark.parametrize('test_name,share_structure,expected_error', [
    ('valid single_share_class', SINGLE_SHARE_CLASS, None)
])
def test_manage_share_structure__share_classes(
        app, session,
        test_name, share_structure, expected_error):
    """Assert that the corp share classes gets set."""
    business = Business()
    business.save()
    err = shares.update_share_structure(business, share_structure['shareStructure'])
    business.save()

    check_business = Business.find_by_internal_id(business.id)
    check_share_classes = check_business.share_classes.all()

    check_share_structure = {'shareStructure': {'shareClasses': []}}
    for s in check_share_classes:
        check_share_structure['shareStructure']['shareClasses'].append(s.json)

    stripped_dict = strip_keys_from_dict(check_share_structure, ['id'])
    assert stripped_dict == share_structure
    assert not err


def test_manage_share_structure__delete_shares(app, session):
    """Assert that the share structures are deleted."""
    from legal_api.models import ShareClass, ShareSeries

    # setup
    business = Business()
    for i in range(5):
        share_class = ShareClass(name=f'share class {i}')
        for j in range(5):
            share_series = ShareSeries(name=f'share series {j}')
            share_class.series.append(share_series)
        business.share_classes.append(share_class)
    business.save()
    business_id = business.id

    # test
    shares.delete_existing_shares(business)
    business.save()

    # check
    check_business = Business.find_by_internal_id(business_id)
    share_classes = check_business.share_classes.all()
    assert not share_classes

    share_classes = session.query(ShareClass).all()
    assert not share_classes

    share_class_version = version_class(ShareClass)
    share_class_versions = session.query(share_class_version).all()
    assert len(share_class_versions) == 5
    for scv in share_class_versions:
        assert scv.operation_type == 2

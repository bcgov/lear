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
"""The Unit Tests for the business filing component processors."""
import random

import pytest
from business_model.models import Business
from sql_versioning import version_class

from business_filer.filing_processors.filing_components import shares
from tests import strip_keys_from_dict


@pytest.fixture(scope="function", autouse=True)
def clean_business():
    pass

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
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = Business(identifier=identifier)
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
    from business_model.models import ShareClass, ShareSeries
   
    # setup
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = Business(identifier=identifier)
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

    share_class_version = version_class(ShareClass)
    share_class_versions = session.query(share_class_version).all()
    assert len(share_class_versions) > 0
    for scv in share_class_versions:
        assert scv.operation_type in (0, 2)
        # assert scv.operation_type == 2

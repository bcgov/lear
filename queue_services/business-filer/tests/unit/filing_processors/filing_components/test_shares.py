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
from datetime import date
from business_model.models import Business, Resolution
from sql_versioning import version_class

from business_filer.filing_processors.filing_components import shares
from tests import strip_keys_from_dict


@pytest.fixture(scope="function", autouse=True)
def clean_business():
    pass

@pytest.mark.parametrize('test_name,resolution_dates,expected_error', [
    ('valid_resolution_dates', [], None),
    ('valid_resolution_dates_string', ['2020-05-23'], None),
    ('valid_multiple_resolution_dates_string', ['2020-05-23', '2020-06-01'], None),
    ('invalid_resolution_dates_string', ['2020-05-23', 'error'], "Invalid isoformat string: 'error'"),
    ('valid_resolution_dates_obj', [{'date':'2020-05-23'}], None),
    ('valid_multiple_resolution_dates_obj', [{'date':'2020-05-23'},{'date':'2020-06-01'}], None),
    ('invalid_resolution_dates_obj', [{'date':'error'}], "Invalid isoformat string: 'error'")
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
    if test_name == "valid_multiple_resolution_dates":
        resolution = Resolution(
            resolution_date=date.fromisoformat('2023-01-01'),
            resolution_type=Resolution.ResolutionType.SPECIAL.value
        )
        business.resolutions.append(resolution)
        business.save()
        resolution_dates[0]['id'] = resolution.id
    try:
        shares.update_share_structure(business, new_data['shareStructure'], True)
        business.save()
        if 'id' in resolution_dates[0]:
            del resolution_dates[0]['id']
    except Exception as ex:
        err = ex

    if expected_error:
        assert str(err) == expected_error
    else:
        check_business = Business.find_by_internal_id(business.id)
        check_resolution = check_business.resolutions.all()
        assert len(check_resolution) == len(resolution_dates)
        if test_name.endswith('_obj'):
            assert set([d['date'] for d in resolution_dates]) == \
                set([x.resolution_date.isoformat() for x in check_resolution])
        else:
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
            'currencyAdditional': None,
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
    shares.update_share_structure(business, share_structure['shareStructure'])
    business.save()

    check_business = Business.find_by_internal_id(business.id)
    check_share_classes = check_business.share_classes.all()

    check_share_structure = {'shareStructure': {'shareClasses': []}}
    for s in check_share_classes:
        check_share_structure['shareStructure']['shareClasses'].append(s.json)

    stripped_dict = strip_keys_from_dict(check_share_structure, ['id'])
    assert stripped_dict == share_structure


def test_manage_share_structure__create_persists_currency_additional(app, session):
    """Assert that a created share class persists currencyAdditional (grandfathered OTHER)."""
    share_structure = {
        "shareClasses": [{
            "name": "Class A",
            "priority": 1,
            "maxNumberOfShares": 100,
            "parValue": 1,
            "currency": "OTHER",
            "currencyAdditional": "Bitcoin",
            "hasMaximumShares": True,
            "hasParValue": True,
            "hasRightsOrRestrictions": False,
            "series": []
        }]
    }
    business = Business()
    business.save()

    shares.update_share_structure(business, share_structure)
    business.save()

    check_business = Business.find_by_internal_id(business.id)
    persisted = check_business.share_classes.all()
    assert len(persisted) == 1
    assert persisted[0].currency == "OTHER"
    assert persisted[0].currency_additional == "Bitcoin"


def test_manage_share_structure_correction__update_clears_currency_additional(app, session):
    """Assert that switching OTHER -> CAD via correction clears currency_additional."""
    from business_model.models import ShareClass

    # setup: existing grandfathered OTHER class
    business = Business()
    existing = ShareClass(
        name="Class A",
        priority=1,
        max_share_flag=True,
        max_shares=100,
        par_value_flag=True,
        par_value=1,
        currency="OTHER",
        currency_additional="Bitcoin",
        special_rights_flag=False
    )
    business.share_classes.append(existing)
    business.save()
    existing_id = existing.id

    # correction submits: same class, currency replaced, currencyAdditional null
    share_structure = {
        "shareClasses": [{
            "id": existing_id,
            "name": "Class A",
            "priority": 1,
            "maxNumberOfShares": 100,
            "parValue": 1,
            "currency": "CAD",
            "currencyAdditional": None,
            "hasMaximumShares": True,
            "hasParValue": True,
            "hasRightsOrRestrictions": False,
            "series": []
        }]
    }

    shares.update_share_structure_correction(business, share_structure)
    business.save()

    updated = ShareClass.find_by_share_class_id(existing_id)
    assert updated.currency == "CAD"
    assert updated.currency_additional is None


def test_manage_share_structure_correction__update_preserves_currency_additional(app, session):
    """Assert that correcting an OTHER class without changing currency preserves currency_additional."""
    from business_model.models import ShareClass

    # setup: existing grandfathered OTHER class
    business = Business()
    existing = ShareClass(
        name="Class A",
        priority=1,
        max_share_flag=True,
        max_shares=100,
        par_value_flag=True,
        par_value=1,
        currency="OTHER",
        currency_additional="Bitcoin",
        special_rights_flag=False
    )
    business.share_classes.append(existing)
    business.save()
    existing_id = existing.id

    # correction submits: same class with name change, currency still OTHER, freetext preserved
    share_structure = {
        "shareClasses": [{
            "id": existing_id,
            "name": "Class A Renamed",
            "priority": 1,
            "maxNumberOfShares": 100,
            "parValue": 1,
            "currency": "OTHER",
            "currencyAdditional": "Bitcoin",
            "hasMaximumShares": True,
            "hasParValue": True,
            "hasRightsOrRestrictions": False,
            "series": []
        }]
    }

    shares.update_share_structure_correction(business, share_structure)
    business.save()

    updated = ShareClass.find_by_share_class_id(existing_id)
    assert updated.name == "Class A Renamed"
    assert updated.currency == "OTHER"
    assert updated.currency_additional == "Bitcoin"


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
    share_class_versions = session.query(share_class_version).filter_by(business_id=business_id).all()
    assert len(share_class_versions) > 0
    for scv in share_class_versions:
        assert scv.operation_type in (0, 2)
        # assert scv.operation_type == 2

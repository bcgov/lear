# Copyright © 2026 Province of British Columbia
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

"""Tests for the ShareObject model."""
from unittest.mock import MagicMock

from colin_api.models import ShareObject


def test_get_share_classes_carries_other_currency():
    """Assert the OTH free-text currency is read and serialized as currencyAdditional."""
    cursor = MagicMock()
    cursor.description = [
        ('SHARE_CLASS_ID',), ('CURRENCY_TYP_CD',), ('MAX_SHARE_IND',), ('SHARE_QUANTITY',),
        ('SPEC_RIGHTS_IND',), ('PAR_VALUE_IND',), ('PAR_VALUE_AMT',), ('CLASS_NME',), ('OTHER_CURRENCY',)
    ]
    # one class row, then no series rows for it
    cursor.fetchall.side_effect = [
        [(0, 'OTH', 'N', 5000, 'Y', 'Y', 2.0, 'CLASS A', 'BITCOIN')],
        []
    ]

    # pylint: disable-next=protected-access
    share_classes = ShareObject._get_share_classes(cursor, event_id=1, corp_num='0870226')

    assert len(share_classes) == 1
    assert share_classes[0].other_currency == 'BITCOIN'
    assert share_classes[0].to_dict()['currencyAdditional'] == 'BITCOIN'
    assert share_classes[0].to_dict()['currency'] == 'OTH'

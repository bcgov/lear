# Copyright © 2024 Province of British Columbia
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

"""Tests to assure the Batch Model.

Test-Suite to ensure that the Batch Model is working as expected.
"""

from business_model.models import Batch


def test_valid_batch_save(session):
    """Assert that a valid batch can be saved."""
    batch = Batch(
        batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION,
        status=Batch.BatchStatus.HOLD,
        size=3,
        max_size=10,
        notes=''
    )
    batch.save()
    assert batch.id


def test_find_batch_by_id(session):
    """Assert that the method returns correct value."""
    batch = Batch(
        batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION,
        status=Batch.BatchStatus.HOLD,
        size=3,
        max_size=10,
        notes=''
    )
    batch.save()

    res = Batch.find_by_id(batch.id)

    assert res
    assert res.batch_type == batch.batch_type


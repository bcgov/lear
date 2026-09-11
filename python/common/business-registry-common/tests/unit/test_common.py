# Copyright © 2025 Province of British Columbia
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
"""Tests for Error and BusinessException."""
import pytest

from business_common.errors.errors import Error
from business_common.exceptions.business_exception import BusinessException


def test_error():
    """Assert Error stores code and message list."""
    error = Error(400, [{"message": "Bad Request"}])
    assert error.code == 400
    assert error.msg == [{"message": "Bad Request"}]


def test_business_exception():
    """Assert BusinessException stores error/status_code and is raiseable."""
    with pytest.raises(BusinessException) as exc_info:
        raise BusinessException("not found", 404)
    assert exc_info.value.error == "not found"
    assert exc_info.value.status_code == 404

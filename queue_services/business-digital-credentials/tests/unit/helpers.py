# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from string import ascii_letters, digits
from random import choices

from business_model.models import RegistrationBootstrap


def _generate_characters(length: int = 8):
    allowed_chars = ascii_letters + digits  # a-z, A-Z, 0-9
    return ''.join(choices(allowed_chars, k=length))


def generate_temp_filing():
    temp_identifier = 'Tb' + _generate_characters(8)
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = temp_identifier
    temp_reg.save()
    return temp_identifier

# Copyright © 2019 Province of British Columbia
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

"""Tests to assure the users end-point.

Test-Suite to ensure that the /users endpoint is working as expected.
"""

# import json
# from tests.utilities.schema_assertions import assert_valid_schema


# def test_get_user(client):
#     # Do whatever is necessary to create a user here…

#     response = client.get('/users/1')

#     if not hasattr(response, 'json_data'):
#         # assert False
#         pass
#     else:
#         json_data = json.loads(response.data)

#         assert_valid_schema(json_data, 'user.json')


# def test_get_users(client):

#     raise NotImplementedError

#     rv = client.get('/api/v1/users')
#     print('get users', rv.json)
#     assert False

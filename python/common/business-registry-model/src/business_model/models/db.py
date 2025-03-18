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
"""Create SQLAlchenmy and Schema managers.

These will get initialized by the application using the models
"""
from flask_sqlalchemy import SQLAlchemy
from sql_versioning import versioned_session

db = SQLAlchemy()  # pylint: disable=invalid-name
versioned_session(db.session)
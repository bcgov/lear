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

"""Manage the database and some other items required to run the API
"""
import logging

from flask_script import Manager  # class for handling a set of commands
from flask_migrate import Migrate, MigrateCommand

from tracker.app import create_app
from tracker.models import db

# models included so that migrate can build the database migrations
import tracker.models  # pylint: disable=unused-import

APP = create_app()
MIGRATE = Migrate(APP, db)
MANAGER = Manager(APP)

MANAGER.add_command('db', MigrateCommand)

if __name__ == '__main__':
    logging.log(logging.INFO, 'Running the Manager')
    MANAGER.run()

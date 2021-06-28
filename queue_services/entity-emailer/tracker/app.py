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
"""This module is the used specifically for tracker db migration/upgrade purposes."""

import os

from flask import Flask  # noqa: I001
from .config import get_named_config
from .models import db
from .models import __all__ as models

def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    config = get_named_config(run_mode)
    app.config.from_object(get_named_config(run_mode))
    # print(f"app.config.DB_NAME: {app.config}")
    db.init_app(app)

    register_shellcontext(app)

    return app

def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {
            'app': app,
            'db': db,
            'models': models}  # pragma: no cover

    app.shell_context_processor(shell_context)

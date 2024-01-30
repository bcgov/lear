# Copyright © 2023 Province of British Columbia
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
"""The Entity Auth service.

This module is the service worker for updating auth with business data.
"""
from __future__ import annotations

from business_model import db
from flask import Flask

from .config import Config, Production
from .resources import register_endpoints
from .services import queue
from .utils import get_run_version


def create_app(environment: Config = Production, **kwargs) -> Flask:
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(environment)

    db.init_app(app)
    queue.init_app(app)
    register_endpoints(app)

    return app

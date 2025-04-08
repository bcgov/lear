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
"""The furnishings job.

This module is the job worker for involuntary dissolution furnishing tasks.
"""
import os

from flask import Flask

from business_model.models import db
from furnishings.config import DevelopmentConfig, ProductionConfig, UnitTestingConfig
from furnishings.services import flags, gcp_queue, post_processor, stage_one_processor
from structured_logging import StructuredLogging

CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": UnitTestingConfig,
    "production": ProductionConfig
}

def create_app(environment: str = os.getenv("DEPLOYMENT_ENV", "production"), **kwargs):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.logger = StructuredLogging(app).get_logger()
    app.config.from_object(CONFIG_MAP.get(environment, "production"))
    flags.init_app(app, kwargs.get("ld_test_data"))
    db.init_app(app)
    gcp_queue.init_app(app)
    stage_one_processor.init_app(app, gcp_queue)
    post_processor.init_app(app)
    register_shellcontext(app)

    return app


def register_shellcontext(app: Flask):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {
            "app": app,
            "db": db
        }

    app.shell_context_processor(shell_context)

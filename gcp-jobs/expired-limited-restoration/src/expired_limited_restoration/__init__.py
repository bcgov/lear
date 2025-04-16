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
"""The Expired Limited Restoration service.

This module is being used to process businesses with expired limited restorations.
"""
import os

from dotenv import find_dotenv, load_dotenv
from flask import Flask
from structured_logging import StructuredLogging

from expired_limited_restoration.config import DevConfig, TestConfig, ProdConfig

CONFIG_MAP = {
    "development": DevConfig,
    "testing": TestConfig,
    "production": ProdConfig
}


# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

def create_app(environment: str = os.getenv("DEPLOYMENT_ENV", "production"), **kwargs):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.logger = StructuredLogging(app).get_logger()
    app.config.from_object(CONFIG_MAP.get(environment))

    return app

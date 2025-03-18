# Copyright © 2023 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""
This module is used for setting up various configurations for the application.
Each configuration inherits from the base configuration and can override the properties as needed.

The `Config` class contains the base configuration with common settings for all environments.

The `Production`, `Sandbox`, `Development`, and `Testing` classes set specific settings for each environment.

Environment variables are used to store the necessary values for each setting.
"""

import os

from dotenv import find_dotenv
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv(find_dotenv())


class Config:  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults.

    Used as the base for all the other configurations.
    """

    DEBUG = False
    TESTING = False

    DB_USER = os.getenv("DATABASE_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_NAME", "")
    DB_HOST = os.getenv("DATABASE_HOST", "")
    DB_PORT = int(os.getenv("DATABASE_PORT", "5432"))  # POSTGRESQL
    # POSTGRESQL
    if DB_UNIX_SOCKET := os.getenv("DATABASE_UNIX_SOCKET", None):
        SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?host={DB_UNIX_SOCKET}"
    else:
        SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class Production(Config):  # pylint: disable=too-few-public-methods
    """Production class configuration that should override vars for production.
    """
    DEBUG = False
    TESTING = False


class Sandbox(Config):  # pylint: disable=too-few-public-methods
    """Sandbox class configuration that should override vars for Sandbox.
    """

    DEVELOPMENT = True
    DEBUG = True


class Migration:  # pylint: disable=too-few-public-methods
    """Config for db migration."""

    TESTING = False
    DEBUG = True

    DB_USER = os.getenv("DATABASE_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_NAME", "")
    DB_HOST = os.getenv("DATABASE_HOST", "")
    DB_PORT = int(os.getenv("DATABASE_PORT", "5432"))  # POSTGRESQL
    # POSTGRESQL
    if DB_UNIX_SOCKET := os.getenv("DATABASE_UNIX_SOCKET", None):
        SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?host={DB_UNIX_SOCKET}"
    else:
        SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class Development(Config):  # pylint: disable=too-few-public-methods
    """Development class configuration that should override vars for Development.
    """

    DEVELOPMENT = True
    DEBUG = True


class Testing(Config):  # pylint: disable=too-few-public-methods
    """Testing class configuration that should override vars for Testing.
    """

    TESTING = True

    DATABASE_TEST_USERNAME = os.getenv("DATABASE_TEST_USERNAME", "")
    DATABASE_TEST_PASSWORD = os.getenv("DATABASE_TEST_PASSWORD", "")
    DATABASE_TEST_NAME = os.getenv("DATABASE_TEST_NAME", "")
    DATABASE_TEST_HOST = os.getenv("DATABASE_TEST_HOST", "")
    DATABASE_TEST_PORT = int(os.getenv("DATABASE_TEST_PORT", "5432"))  # POSTGRESQL

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{DATABASE_TEST_USERNAME}:{DATABASE_TEST_PASSWORD}@"
        f"{DATABASE_TEST_HOST}:{DATABASE_TEST_PORT}/{DATABASE_TEST_NAME}"
    )
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
Module Name: Blueprint Ops
Description: This module contains routes that are used to check the health and readiness of the API.
The module includes two routes, "/healthz", and "/readyz", which respond with status messages indicating the health and
readiness of the API respectively.
Health is determined by the ability to execute a simple SELECT 1 query on the connected database.
"""
from http import HTTPStatus

from flask import Blueprint, current_app
from sqlalchemy import exc, text

from business_model.models import db

bp = Blueprint("ops", __name__)


@bp.route("/healthz", methods=("GET",))
def health():
    """Check the health of the API."""
    try:
        db.session.execute(text("select 1"))
    except exc.SQLAlchemyError as db_exception:
        current_app.logger.error("DB connection pool unhealthy:" + repr(db_exception))
        return {"message": "api is down"}, HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as default_exception:  # noqa: B902; log error
        current_app.logger.error("DB connection failed:" + repr(default_exception))
        return {"message": "api is down"}, 500

    current_app.logger.info("/ops/healthz")
    return {"message": "api is healthy"}, HTTPStatus.OK


@bp.route("/readyz", methods=("GET",))
def ready():
    """Return service is setup and ready to work."""
    current_app.logger.info("/ops/readyz")
    return {"message": "api is ready"}, HTTPStatus.OK
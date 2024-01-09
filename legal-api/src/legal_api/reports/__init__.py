# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
"""Module to manage the calls and content to the reporting service."""
from http import HTTPStatus

from flask import jsonify
from flask_babel import _

from .report import Report


def get_pdf(filing, report_type=None):
    """Render a PDF for the supplied filing."""
    try:
        return Report(filing).get_pdf(report_type)
    except FileNotFoundError:
        # We don't have a template for it, so it must only be available on paper.
        return jsonify({"message": _("Available on paper only.")}), HTTPStatus.NOT_FOUND

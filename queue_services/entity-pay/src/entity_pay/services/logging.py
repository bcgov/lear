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
"""Structured logging based on emitting to knative."""
import inspect
import json
import os

from werkzeug.local import LocalProxy


def structured_log(request: LocalProxy, severity: str = "NOTICE", message: str = None):
    """Prints structured log message"""
    frm = inspect.stack()[1]
    mod = inspect.getmodule(frm[0])

    # Build structured log messages as an object.
    global_log_fields = {}

    if project := os.environ.get("GOOGLE_CLOUD_PROJECT"):
        # Add log correlation to nest all log messages.
        trace_header = request.headers.get("X-Cloud-Trace-Context")

        if trace_header and project:
            trace = trace_header.split("/")
            global_log_fields["logging.googleapis.com/trace"] = f"projects/{project}/traces/{trace[0]}"

    # Complete a structured log entry.
    entry = {
        "severity": severity,
        "message": message,
        # Log viewer accesses 'component' as jsonPayload.component'.
        "component": f"{mod.__name__}.{frm.function}",
        **global_log_fields,
    }

    print(json.dumps(entry))

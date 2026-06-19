# Copyright (c) 2026, Province of British Columbia

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Common helper functions for reports flows."""
from typing import Optional

import pycountry
from flask import current_app


def get_amalg_formatted_jurisdiction(identifier: str, country_code: str, region_code: Optional[str] = None):
    """Return the jurisdiction region if its in Canada otherwise return the jurisdiction country."""
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        region = None
        # NOTE: Region code is being saved as 'FEDERAL' in lear and 'FD' in colin
        if country_code == "CA" and region_code.upper() in ["FEDERAL", "FD"]:
            return "Federal"
        elif country_code == "CA" and region_code:
            region = pycountry.subdivisions.get(code=f"{country_code}-{region_code}")

        return region.name if region else country.name

    except (AttributeError, LookupError) as err:
        current_app.logger.warning("Unable to get jurisdiction for amalgmating company: %s, country_code: %s, region_code: %s, err: %s",
                                   identifier,
                                   country_code,
                                   region_code,
                                   err.with_traceback(None))
        return "N/A"

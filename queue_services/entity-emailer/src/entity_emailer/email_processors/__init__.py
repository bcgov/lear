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
"""This module contains all of the Entity Email specific processors.

Processors hold the business logic for how an email is interpreted and sent.
"""
from pathlib import Path


def substitute_template_parts(template_code):
    """Substitute template parts in main template.

    Template parts are marked by [[partname.html]] in templates.

    This functionality is restricted by:
    - markup must be exactly [[partname.html]] and have no extra spaces around file name
    - template parts can only be one level deep, ie: this rudimentary framework does not handle nested template
    parts. There is no recursive search and replace.

    :param template_code: string
    :return: template_code string, modified.
    """
    template_parts = [
        'business-dashboard-link',
        'business-info',
        'cra-notice',
        'footer',
        'header',
        'initiative-notice',
        'logo',
        'partners',
        'pdf-notice',
        'style',
        'whitespace-16px',
        'whitespace-24px'
    ]

    # substitute template parts - marked up by [[filename]]
    for template_part in template_parts:
        template_part_code = Path(f'email_templates/common/{template_part}.html').read_text()
        template_code = template_code.replace('[[{}.html]]'.format(template_part), template_part_code)

    return template_code

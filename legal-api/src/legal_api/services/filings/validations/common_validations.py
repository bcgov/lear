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
"""Common validations share through the different filings."""
from legal_api.errors import Error


def validate_share_structure(incorporation_json, filing_type) -> Error:  # pylint: disable=too-many-branches
    """Validate the share structure data of the incorporation filing."""
    share_classes = incorporation_json['filing'][filing_type] \
        .get('shareStructure', {}).get('shareClasses', [])
    msg = []
    memoize_names = []

    for index, item in enumerate(share_classes):
        if item['name'] in memoize_names:
            err_path = '/filing/{0}/shareClasses/{1}/name/'.format(filing_type, index)
            msg.append({'error': 'Share class %s name already used in a share class or series.' % item['name'],
                        'path': err_path})
        else:
            memoize_names.append(item['name'])

        if item['hasMaximumShares']:
            if not item.get('maxNumberOfShares', None):
                err_path = '/filing/{0}/shareClasses/{1}/maxNumberOfShares/'.format(filing_type, index)
                msg.append({'error': 'Share class %s must provide value for maximum number of shares' % item['name'],
                            'path': err_path})
        if item['hasParValue']:
            if not item.get('parValue', None):
                err_path = '/filing/{0}/shareClasses/{1}/parValue/'.format(filing_type, index)
                msg.append({'error': 'Share class %s must specify par value' % item['name'], 'path': err_path})
            if not item.get('currency', None):
                err_path = '/filing/{0}/shareClasses/{1}/currency/'.format(filing_type, index)
                msg.append({'error': 'Share class %s must specify currency' % item['name'], 'path': err_path})
        response = validate_series(item, memoize_names, filing_type, index)
        if response:
            msg.extend(response)

    if msg:
        return msg

    return None


def validate_series(item, memoize_names, filing_type, index) -> Error:
    """Validate the series in the shareStructure."""
    msg = []
    for series_index, series in enumerate(item.get('series', [])):
        err_path = '/filing/{0}/shareClasses/{1}/series/{2}'.format(filing_type, index, series_index)
        if series['name'] in memoize_names:
            msg.append({'error': 'Share series %s name already used in a share class or series.' % series['name'],
                        'path': err_path})
        else:
            memoize_names.append(series['name'])

        if series['hasMaximumShares']:
            if not series.get('maxNumberOfShares', None):
                msg.append({
                    'error': 'Share series %s must provide value for maximum number of shares' % series['name'],
                    'path': '%s/maxNumberOfShares' % err_path
                })
            else:
                if item['hasMaximumShares'] and item.get('maxNumberOfShares', None) and \
                        int(series['maxNumberOfShares']) > int(item['maxNumberOfShares']):
                    msg.append({
                        'error': 'Series %s share quantity must be less than or equal to that of its class %s'
                                 % (series['name'], item['name']),
                        'path': '%s/maxNumberOfShares' % err_path
                    })
    return msg

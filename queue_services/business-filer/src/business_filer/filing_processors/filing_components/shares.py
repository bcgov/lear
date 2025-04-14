# Copyright © 2020 Province of British Columbia
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
"""Manages the share structure for a business."""
from __future__ import annotations

from typing import Dict, List, Optional

from dateutil.parser import parse
from business_model.models import Business, Resolution, ShareClass, ShareSeries


def update_share_structure(business: Business, share_structure: Dict) -> Optional[List]:
    """Manage the share structure for a business.

    Assumption: The structure has already been validated, upon submission.

    Other errors are recorded and will be managed out of band.
    """
    if not business or not share_structure:
        # if nothing is passed in, we don't care and it's not an error
        return None

    err = []

    if resolution_dates := share_structure.get('resolutionDates'):
        for resolution_dt in resolution_dates:
            try:
                d = Resolution(
                    resolution_date=parse(resolution_dt).date(),
                    resolution_type=Resolution.ResolutionType.SPECIAL.value
                )
                business.resolutions.append(d)
            except (ValueError, OverflowError):
                err.append(
                    {'error_code': 'FILER_INVALID_RESOLUTION_DATE',
                     'error_message': f"Filer: invalid resolution date:'{resolution_dt}'"}
                )

    if share_classes := share_structure.get('shareClasses'):
        try:
            delete_existing_shares(business)
        except:  # noqa:E722 pylint: disable=bare-except; catch all exceptions
            err.append(
                {'error_code': 'FILER_UNABLE_TO_DELETE_SHARES',
                 'error_message': f"Filer: unable to delete shares for :'{business.identifier}'"}
            )
            # we're FUBAR, do not load the new shares
            return err

        try:
            for share_class_info in share_classes:
                share_class = create_share_class(share_class_info)
                business.share_classes.append(share_class)
        except KeyError:
            err.append(
                {'error_code': 'FILER_UNABLE_TO_SAVE_SHARES',
                 'error_message': f"Filer: unable to save new shares for :'{business.identifier}'"}
            )

    return err


def update_resolution_dates_correction(business: Business, share_structure: Dict) -> List:
    """Correct resolution dates by adding or removing."""
    err = []

    inclusion_entries = []
    exclusion_entries = []
    # Delete the ones that are present in db but not in the json and create the ones in json but not in db.
    if resolution_dates := share_structure.get('resolutionDates'):
        # Two lists of dates in datetime format
        business_dates = [item.resolution_date for item in business.resolutions]
        parsed_dates = [parse(resolution_dt).date() for resolution_dt in resolution_dates]

        # Dates in both db and json
        inclusion_entries = [business.resolutions[index] for index, date in enumerate(business_dates)
                             if date in parsed_dates]
        if len(inclusion_entries) > 0:
            business.resolutions = inclusion_entries
        else:
            business.resolutions = []

        # Dates in json and not in db
        exclusion_entries = [date for date in parsed_dates if date not in business_dates]

        resolution_dates = exclusion_entries

        for resolution_dt in resolution_dates:
            try:
                d = Resolution(
                    resolution_date=resolution_dt,
                    resolution_type=Resolution.ResolutionType.SPECIAL.value
                )
                business.resolutions.append(d)
            except (ValueError, OverflowError):
                err.append(
                    {'error_code': 'FILER_INVALID_RESOLUTION_DATE',
                     'error_message': f"Filer: invalid resolution date:'{resolution_dt}'"}
                )
    else:
        business.resolutions = []

    return err


def update_share_structure_correction(business: Business, share_structure: Dict) -> Optional[List]:
    """Manage the share structure for a business.

    Assumption: The structure has already been validated, upon submission.

    Other errors are recorded and will be managed out of band.
    """
    if not business or not share_structure:
        # if nothing is passed in, we don't care and it's not an error
        return None

    err = update_resolution_dates_correction(business, share_structure)

    if share_classes := share_structure.get('shareClasses'):
        # Entries in json and not in db
        exclusion_entries = []

        # Update existing ones in both db and json, append the ones only in json into exclusion entires
        update_business_share_class(share_classes, business, exclusion_entries)

        try:
            for share_class_info in exclusion_entries:
                share_class = create_share_class(share_class_info)
                business.share_classes.append(share_class)
        except KeyError:
            err.append(
                {'error_code': 'FILER_UNABLE_TO_SAVE_SHARES',
                 'error_message': f"Filer: unable to save new shares for :'{business.identifier}'"}
            )

    return err


def delete_existing_shares(business: Business):
    """Delete the existing share classes and series for a business."""
    if existing_shares := business.share_classes.all():
        for share_class in existing_shares:
            business.share_classes.remove(share_class)


def create_share_class(share_class_info: dict) -> ShareClass:
    """Create a new share class and associated series."""
    share_class = ShareClass(
        name=share_class_info['name'],
        priority=share_class_info['priority'],
        max_share_flag=share_class_info['hasMaximumShares'],
        max_shares=share_class_info.get('maxNumberOfShares', None),
        par_value_flag=share_class_info['hasParValue'],
        par_value=share_class_info.get('parValue', None),
        currency=share_class_info.get('currency', None),
        special_rights_flag=share_class_info['hasRightsOrRestrictions']
    )
    share_class.series = []
    for series in share_class_info['series']:
        share_series = ShareSeries(
            name=series['name'],
            priority=series['priority'],
            max_share_flag=series['hasMaximumShares'],
            max_shares=series.get('maxNumberOfShares', None),
            special_rights_flag=series['hasRightsOrRestrictions']
        )
        share_class.series.append(share_series)

    return share_class


def update_business_share_class(share_classes: list, business: Business, exclusion_entries: list):
    """Update existing ones in both db if they are present in json."""
    share_class_db_ids = [item.id for item in business.share_classes]

    inclusion_entries = []
    for share_class_info in share_classes:
        if share_class_info.get('id') in share_class_db_ids:
            share_class = ShareClass.find_by_share_class_id(share_class_info.get('id'))
            if share_class:
                update_share_class(share_class, share_class_info)
                inclusion_entries.append(share_class)
            else:
                exclusion_entries.append(share_class_info)
        else:
            exclusion_entries.append(share_class_info)

    business.share_classes = inclusion_entries


def update_share_class(share_class: ShareClass, share_class_info: dict):
    """Update share class instance in db."""
    share_class.name = share_class_info['name']
    share_class.priority = share_class_info['priority']
    share_class.max_share_flag = share_class_info['hasMaximumShares']
    share_class.max_shares = share_class_info.get('maxNumberOfShares', None)
    share_class.par_value_flag = share_class_info['hasParValue']
    share_class.par_value = share_class_info.get('parValue', None)
    share_class.currency = share_class_info.get('currency', None)
    share_class.special_rights_flag = share_class_info['hasRightsOrRestrictions']

    # array of ids for share series instance from db
    share_class_series_ids = []
    if len(share_class.series) > 0:
        share_class_series_ids = [series.id for series in share_class.series]

    inclusion_series = []
    # update existing series in db and create new series if not exist
    for series_info in share_class_info.get('series'):
        series_id = series_info.get('id')
        if series_id in share_class_series_ids:
            series_index = share_class_series_ids.index(series_id)
            series = share_class.series[series_index]
            update_share_series(series_info, series)
            inclusion_series.append(series)
        else:
            new_share_series = ShareSeries()
            update_share_series(series_info, new_share_series)
            inclusion_series.append(new_share_series)
    share_class.series = inclusion_series


def update_share_series(series_info: dict, series: ShareSeries):
    """Update share series."""
    series.name = series_info['name']
    series.priority = series_info['priority']
    series.max_share_flag = series_info['hasMaximumShares']
    series.max_shares = series_info.get('maxNumberOfShares', None)
    series.special_rights_flag = series_info['hasRightsOrRestrictions']

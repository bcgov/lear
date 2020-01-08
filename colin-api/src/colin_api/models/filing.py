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
"""Meta information about the service.

Currently this only provides API versioning information
"""
import datetime

from flask import current_app

from colin_api.exceptions import FilingNotFoundException, InvalidFilingTypeException
from colin_api.models import Address, Business, Director, EntityName, Office
from colin_api.resources.db import DB
from colin_api.utils import convert_to_json_date, convert_to_json_datetime


class Filing:
    """Class to contain all model-like functions such as getting and setting from database."""

    # in order of number filed by coops as of september 2019
    FILING_TYPES = {'OTANN': 'annualReport',
                    'OTCDR': 'changeOfDirectors',
                    'OTSPE': 'specialResolution',
                    'OTINC': 'incorporationApplication',
                    'OTAMA': 'amalgamationApplication',
                    'OTADD': 'changeOfAddress',
                    'OTDIS': 'dissolved',
                    'OTCGM': 'amendedAGM',
                    'OTVDS': 'voluntaryDissolution',
                    'OTNCN': 'changeOfName',
                    'OTRES': 'restorationApplication',
                    'OTAMR': 'amendedAnnualReport',
                    'OTADR': 'amendedChangeOfDirectors',
                    'OTVLQ': 'voluntaryLiquidation',
                    'OTNRC': 'appointReceiver',
                    'OTCON': 'continuedOut'
                    }

    # dicts containing data
    business = None
    header = None
    body = None
    filing_type = None
    paper_only = None
    effective_date = None

    def __init__(self):
        """Initialize with all values None."""

    def get_corp_num(self):
        """Get corporation num, aka identifier."""
        return self.business.business['identifier']

    def get_certified_by(self):
        """Get last name; currently is whole name."""
        return self.header['certifiedBy']

    def get_email(self):
        """Get email address."""
        return self.header['email']

    def as_dict(self):
        """Return dict of object that can be json serialized and fits schema requirements."""
        filing = {
            'filing': {
                'header': self.header,
                'business': self.business.business,
            }
        }
        possible_filings = [self.FILING_TYPES[key] for key in self.FILING_TYPES]
        entered_filings = [x for x in self.body.keys() if x in possible_filings]

        if entered_filings:  # filing object possibly storing multiple filings
            for key in entered_filings:
                filing['filing'].update({key: self.body[key]})
        else:  # filing object storing 1 filing
            filing['filing'].update({self.filing_type: self.body})

        return filing

    @classmethod
    def _get_event_id(cls, cursor, corp_num, event_type='FILE'):
        """Get next event ID for filing.

        :param cursor: oracle cursor
        :return: (int) event ID
        """
        try:
            cursor.execute("""select noncorp_event_seq.NEXTVAL from dual""")
            row = cursor.fetchone()
            event_id = int(row[0])

            cursor.execute("""
                INSERT INTO event (event_id, corp_num, event_typ_cd, event_timestmp, trigger_dts)
                  VALUES (:event_id, :corp_num, :event_type, sysdate, NULL)
                """,
                           event_id=event_id,
                           corp_num=corp_num,
                           event_type=event_type
                           )
        except Exception as err:
            current_app.logger.error('Error in filing: Failed to create new event.')
            raise err

        return event_id

    @classmethod
    def _get_events(cls, identifier: str = None, filing_type_code: str = None):
        """Get all event ids of filings for given filing type for this corp."""
        if not identifier or not filing_type_code:
            return None

        try:
            cursor = DB.connection.cursor()
            cursor.execute(
                """
                select event.event_id, event.event_timestmp, filing.period_end_dt
                from event
                join filing on event.event_id = filing.event_id
                where corp_num=:identifier and filing_typ_cd=:filing_type
                """,
                filing_type=filing_type_code,
                identifier=identifier
            )

            events = cursor.fetchall()
            event_list = []
            for row in events:
                row = dict(zip([x[0].lower() for x in cursor.description], row))
                item = {'id': row['event_id'], 'date': row['event_timestmp']}

                # if filing type is an AR include the period_end_dt info
                if Filing.FILING_TYPES[filing_type_code] == 'annualReport':
                    item['annualReportDate'] = row['period_end_dt']

                event_list.append(item)

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error('error getting events for {}'.format(identifier))
            raise err

        return event_list

    @classmethod
    def _create_filing(cls, cursor, event_id, corp_num, ar_date,  # pylint: disable=too-many-arguments;
                       agm_date, filing_type_code='FILE'):
        """Add record to FILING.

        Note: Period End Date and AGM Date are both the AGM Date value for Co-ops.

        :param cursor: oracle cursor
        :param event_id: (int) event_id for all events for this transaction
        :param date: (str) period_end_date
        :param filing_type_code: (str) filing type code
        """
        try:
            if filing_type_code == 'OTANN':
                cursor.execute("""
                    INSERT INTO filing (event_id, filing_typ_cd, effective_dt, period_end_dt, agm_date, arrangement_ind,
                    ods_typ_cd)
                    VALUES (:event_id, :filing_type_code, sysdate, TO_DATE(:period_end_date, 'YYYY-mm-dd'),
                    TO_DATE(:agm_date, 'YYYY-mm-dd'), 'N', 'P')
                    """,
                               event_id=event_id,
                               filing_type_code=filing_type_code,
                               period_end_date=ar_date if not agm_date else agm_date,
                               agm_date=agm_date
                               )
            elif filing_type_code == 'OTADD' or 'OTCDR':
                cursor.execute("""
                    INSERT INTO filing (event_id, filing_typ_cd, effective_dt, period_end_dt)
                      VALUES (:event_id, :filing_type_code, sysdate, TO_DATE(:period_end_date, 'YYYY-mm-dd'))
                    """,
                               event_id=event_id,
                               filing_type_code=filing_type_code,
                               period_end_date=ar_date,
                               )
            else:
                current_app.logger.error(f'error in filing: Did not recognize filing type code: {filing_type_code}')
                raise InvalidFilingTypeException(filing_type=filing_type_code)
        except Exception as err:
            current_app.logger.error(f'error in filing: could not create filing {filing_type_code} for {corp_num}')
            raise err

    @classmethod
    def _create_filing_user(cls, cursor, event_id, filing, user_id):
        """Add to the FILING_USER table.

        :param cursor: oracle cursor
        :param event_id: (int) event_id for all events for this transaction
        :param filing: (obj) Filing data object
        """
        try:
            cursor.execute("""
                INSERT INTO filing_user (event_id, user_id, last_nme, first_nme, middle_nme, email_addr, party_typ_cd,
                role_typ_cd)
                  VALUES (:event_id, :user_id, :last_name, NULL, NULL, :email_address, NULL, NULL)
                """,
                           event_id=event_id,
                           user_id=user_id,
                           last_name=filing.get_certified_by(),
                           email_address=filing.get_email()
                           )
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _add_ledger_text(cls, cursor, event_id, text, user_id):
        """Add note to ledger test table.

        :param cursor: oracle cursor
        :param event_id: (int) event id for corresponding event
        :param text: (str) note for ledger
        """
        try:
            cursor.execute("""
                INSERT INTO ledger_text (event_id, ledger_text_dts, notation, dd_event_id, user_id)
                  VALUES (:event_id, sysdate, :notation, :dd_event_id, :user_id)
                """,
                           event_id=event_id,
                           notation=text,
                           dd_event_id=event_id,
                           user_id=user_id
                           )
        except Exception as err:
            current_app.logger.error(f'Failed to add ledger text: "{text}" for event {event_id}')
            raise err

    @classmethod
    def _get_filing_event_info(cls,  # pylint: disable=too-many-arguments,too-many-branches;
                               identifier: str = None, event_id: str = None, filing_type_cd: str = None,
                               year: int = None):
        """Get the basic filing info that we care about for all filings."""
        # build base querystring
        querystring = ("""
            select event.event_id, event_timestmp, first_nme, middle_nme, last_nme, email_addr, period_end_dt,
            agm_date, effective_dt, event.corp_num, user_id
            from event
            join filing on filing.event_id = event.event_id
            left join filing_user on event.event_id = filing_user.event_id
            where (filing_typ_cd=:filing_type_cd)
            """)

        if identifier:
            querystring += ' AND event.corp_num=:identifier'

        if event_id:
            querystring += ' AND event.event_id=:event_id'

        if year:
            querystring += ' AND extract(year from PERIOD_END_DT)=:year'

        querystring += ' order by EVENT_TIMESTMP desc'

        try:
            cursor = DB.connection.cursor()
            if event_id:
                if year:
                    cursor.execute(querystring, identifier=identifier, event_id=event_id,
                                   filing_type_cd=filing_type_cd, year=year)
                else:
                    cursor.execute(querystring, identifier=identifier, event_id=event_id,
                                   filing_type_cd=filing_type_cd)
            else:
                if year:
                    cursor.execute(querystring, identifier=identifier, filing_type_cd=filing_type_cd, year=year)
                else:
                    cursor.execute(querystring, identifier=identifier, filing_type_cd=filing_type_cd)

            event_info = cursor.fetchone()

            if not event_info:
                raise FilingNotFoundException(identifier=identifier, filing_type=filing_type_cd, event_id=event_id)

            event_info = dict(zip([x[0].lower() for x in cursor.description], event_info))

            # build filing user name from first, middle, last name
            filing_user_name = ' '.join(
                filter(None, [event_info['first_nme'], event_info['middle_nme'], event_info['last_nme']]))
            filing_email = event_info['email_addr']

            if not filing_user_name:
                filing_user_name = 'N/A'

            # if email is blank, set as empty tring
            if not filing_email:
                filing_email = 'xxxx@xxxx.xxx'

            event_info['certifiedBy'] = filing_user_name
            event_info['email'] = filing_email
            event_info['filing_type_code'] = filing_type_cd
            return event_info

        except Exception as err:
            if identifier:
                current_app.logger.error('error getting filing event info for corp {}'.format(identifier))
            else:
                current_app.logger.error('error getting filing event info for event {}'.format(event_id))
            raise err

    @classmethod
    def _get_ar(cls, identifier: str = None, filing_event_info: dict = None):
        """Return annual report filing."""
        # get directors and registered office as of this filing
        director_events = cls._get_events(identifier=identifier, filing_type_code='OTCDR')
        office_events = cls._get_events(identifier=identifier, filing_type_code='OTADD')
        director_event_id = None
        office_event_id = None

        tmp_timestamp = datetime.datetime.fromtimestamp(0)
        for event in director_events:
            if filing_event_info['event_timestmp'] >= event['date'] > tmp_timestamp:
                director_event_id = event['id']
                tmp_timestamp = event['date']
        tmp_timestamp = datetime.datetime.fromtimestamp(0)
        for event in office_events:
            if filing_event_info['event_timestmp'] >= event['date'] > tmp_timestamp:
                office_event_id = event['id']
                tmp_timestamp = event['date']

        recreated_dirs_and_office = True
        if director_event_id:
            try:
                directors = Director.get_by_event(identifier=identifier, event_id=director_event_id)
            except:  # noqa B901; pylint: disable=bare-except;
                # should only get here if agm was before the bob date
                recreated_dirs_and_office = False
                directors = Director.get_current(identifier=identifier)
        else:
            directors = Director.get_current(identifier=identifier)
        directors = [x.as_dict() for x in directors]
        if office_event_id:
            try:
                office_obj_list = (Office.get_by_event(event_id=office_event_id)).as_dict()
                offices = Office.convert_obj_list(office_obj_list)
            except:  # noqa B901; pylint: disable=bare-except;
                # should only get here if agm was before the bob date
                recreated_dirs_and_office = False
                office_obj_list = Office.get_current(identifier=identifier)
                offices = Office.convert_obj_list(office_obj_list)

        else:
            office_obj_list = Office.get_current(identifier=identifier)
            offices = Office.convert_obj_list(office_obj_list)

        filing_obj = Filing()
        filing_obj.body = {
            'annualGeneralMeetingDate': convert_to_json_date(filing_event_info.get('agm_date', None)),
            'annualReportDate': convert_to_json_date(filing_event_info['period_end_dt']),
            'directors': directors,
            'eventId': filing_event_info['event_id'],
            'offices': offices
        }
        filing_obj.filing_type = 'annualReport'
        filing_obj.paper_only = not recreated_dirs_and_office
        filing_obj.effective_date = filing_event_info['period_end_dt']

        return filing_obj

    @classmethod
    def _get_coa(cls, identifier: str = None, filing_event_info: dict = None):
        """Get change of address filing for registered and/or records office."""
        office_obj_list = Office.get_by_event(filing_event_info['event_id'])
        if not office_obj_list:
            raise FilingNotFoundException(identifier=identifier, filing_type='change_of_address',
                                          event_id=filing_event_info['event_id'])

        offices = Office.convert_obj_list(office_obj_list)

        # check to see if this filing was made with an AR -> if it was then set the AR date as the effective date
        effective_date = filing_event_info['event_timestmp']
        annual_reports = cls._get_events(identifier=identifier, filing_type_code='OTANN')
        for filing in annual_reports:
            if convert_to_json_date(filing['date']) == convert_to_json_date(effective_date):
                effective_date = filing['annualReportDate']
                break

        filing_obj = Filing()
        filing_obj.body = {
            'offices': offices,
            'eventId': filing_event_info['event_id']
        }
        filing_obj.filing_type = 'changeOfAddress'
        filing_obj.paper_only = False
        filing_obj.effective_date = effective_date

        return filing_obj

    @classmethod
    def _get_cod(cls, identifier: str = None, filing_event_info: dict = None):
        """Get change of directors filing."""
        director_objs = Director.get_by_event(identifier, filing_event_info['event_id'])
        if len(director_objs) < 3:
            current_app.logger.error('Less than 3 directors for {}'.format(identifier))

        # check to see if this filing was made with an AR -> if it was then set the AR date as the effective date
        effective_date = filing_event_info['event_timestmp']
        annual_reports = cls._get_events(identifier=identifier, filing_type_code='OTANN')
        for filing in annual_reports:
            if convert_to_json_date(filing['date']) == convert_to_json_date(effective_date):
                effective_date = filing['annualReportDate']
                break

        filing_obj = Filing()
        filing_obj.body = {
            'directors': [x.as_dict() for x in director_objs],
            'eventId': filing_event_info['event_id']
        }
        filing_obj.filing_type = 'changeOfDirectors'
        filing_obj.paper_only = False
        filing_obj.effective_date = effective_date

        return filing_obj

    @classmethod
    def _get_con(cls, identifier: str = None, filing_event_info: dict = None):
        """Get change of name filing."""
        name_obj = EntityName.get_by_event(identifier=identifier, event_id=filing_event_info['event_id'])
        if not name_obj:
            raise FilingNotFoundException(identifier=identifier, filing_type='change_of_name',
                                          event_id=filing_event_info['event_id'])

        filing_obj = Filing()
        filing_obj.body = {
            **name_obj.as_dict()
        }
        filing_obj.filing_type = 'changeOfName'
        filing_obj.paper_only = False
        filing_obj.effective_date = filing_event_info['event_timestmp']

        return filing_obj

    @classmethod
    def _get_sr(cls, identifier: str = None, filing_event_info: dict = None):
        """Get special resolution filing."""
        querystring = ("""
            select filing.event_id, filing.effective_dt, ledger_text.notation
            from filing
            join ledger_text on ledger_text.event_id = filing.event_id
            where filing.event_id=:event_id
            """)

        try:
            cursor = DB.connection.cursor()
            cursor.execute(querystring, event_id=filing_event_info['event_id'])
            sr_info = cursor.fetchone()
            if not sr_info:
                raise FilingNotFoundException(identifier=identifier,
                                              filing_type=cls.FILING_TYPES[filing_event_info['filing_type_code']],
                                              event_id=filing_event_info['event_id']
                                              )

            sr_info = dict(zip([x[0].lower() for x in cursor.description], sr_info))
            filing_obj = Filing()
            filing_obj.body = {
                'eventId': sr_info['event_id'],
                'filedDate': convert_to_json_date(sr_info['effective_dt']),
                'resolution': sr_info['notation'],
            }
            filing_obj.filing_type = cls.FILING_TYPES[filing_event_info['filing_type_code']]
            filing_obj.paper_only = True
            filing_obj.effective_date = filing_event_info['event_timestmp']

            return filing_obj

        except Exception as err:
            current_app.logger.error('error getting special resolution filing for corp: {}'.format(identifier))
            raise err

    @classmethod
    def _get_vd(cls, identifier: str = None, filing_event_info: dict = None):
        """Get voluntary dissolution filing."""
        querystring = ("""
                select filing.event_id, filing.effective_dt
                from filing
                where filing.event_id=:event_id
                """)

        try:
            cursor = DB.connection.cursor()
            cursor.execute(querystring, event_id=filing_event_info['event_id'])
            vd_info = cursor.fetchone()
            if not vd_info:
                raise FilingNotFoundException(identifier=identifier,
                                              filing_type=cls.FILING_TYPES[filing_event_info['filing_type_code']],
                                              event_id=filing_event_info['event_id']
                                              )

            vd_info = dict(zip([x[0].lower() for x in cursor.description], vd_info))
            filing_obj = Filing()
            filing_obj.body = {
                'eventId': vd_info['event_id'],
                'dissolutionDate': convert_to_json_date(vd_info['effective_dt'])
            }
            filing_obj.filing_type = cls.FILING_TYPES[filing_event_info['filing_type_code']]
            filing_obj.paper_only = True
            filing_obj.effective_date = filing_event_info['event_timestmp']

            return filing_obj

        except Exception as err:
            current_app.logger.error('error voluntary dissolution filing for corp: {}'.format(identifier))
            raise err

    @classmethod
    def _get_other(cls, identifier: str = None, filing_event_info: dict = None):
        """Get basic info for a filing we aren't handling yet."""
        querystring = ("""
            select filing.event_id, filing.effective_dt, ledger_text.notation
            from filing
            left join ledger_text on ledger_text.event_id = filing.event_id
            where filing.event_id=:event_id
            """)

        try:
            cursor = DB.connection.cursor()
            cursor.execute(querystring, event_id=filing_event_info['event_id'])
            filing_info = cursor.fetchone()
            if not filing_info:
                raise FilingNotFoundException(identifier=identifier,
                                              filing_type=cls.FILING_TYPES[filing_event_info['filing_type_code']],
                                              event_id=filing_event_info['event_id']
                                              )

            filing_info = dict(zip([x[0].lower() for x in cursor.description], filing_info))
            filing_obj = Filing()
            filing_obj.body = {
                'eventId': filing_info['event_id'],
                'filedDate': convert_to_json_date(filing_event_info['event_timestmp']),
                'ledgerText': filing_info['notation'],
            }
            filing_obj.filing_type = cls.FILING_TYPES[filing_event_info['filing_type_code']]
            filing_obj.paper_only = True
            filing_obj.effective_date = filing_info['effective_dt']

            return filing_obj

        except Exception as err:
            current_app.logger.error('error getting {} filing for corp: {}'.format(
                cls.FILING_TYPES[filing_event_info['filing_type_code']], identifier))
            raise err

    @classmethod
    def get_filing(cls, business: Business = None, event_id: str = None, filing_type: str = None, year: int = None):
        """Get a Filing."""
        if not business or not filing_type:
            return None

        try:
            identifier = business.get_corp_num()

            # get the filing types corresponding filing code
            code = [key for key in cls.FILING_TYPES if cls.FILING_TYPES[key] == filing_type]
            if len(code) < 1:
                raise InvalidFilingTypeException(filing_type=filing_type)

            # get the filing event info
            filing_event_info = cls._get_filing_event_info(identifier=identifier, event_id=event_id,
                                                           filing_type_cd=code[0], year=year)
            if not filing_event_info:
                raise FilingNotFoundException(identifier=identifier, filing_type=filing_type, event_id=event_id)

            if filing_type == 'annualReport':
                filing_obj = cls._get_ar(identifier=identifier, filing_event_info=filing_event_info)

            elif filing_type == 'changeOfAddress':
                filing_obj = cls._get_coa(identifier=identifier, filing_event_info=filing_event_info)

            elif filing_type == 'changeOfDirectors':
                filing_obj = cls._get_cod(identifier=identifier, filing_event_info=filing_event_info)

            elif filing_type == 'changeOfName':
                filing_obj = cls._get_con(identifier=identifier, filing_event_info=filing_event_info)

            elif filing_type == 'specialResolution':
                filing_obj = cls._get_sr(identifier=identifier, filing_event_info=filing_event_info)

            elif filing_type == 'voluntaryDissolution':
                filing_obj = cls._get_vd(identifier=identifier, filing_event_info=filing_event_info)

            else:
                # uncomment to bring in other filings as available on paper only
                # filing_obj = cls._get_other(identifier=identifier, filing_event_info=filing_event_info)
                raise InvalidFilingTypeException(filing_type=filing_type)

            filing_obj.header = {
                'availableOnPaperOnly': filing_obj.paper_only,
                'certifiedBy': filing_event_info['certifiedBy'],
                'colinId': filing_obj.body['eventId'],
                'date': convert_to_json_date(filing_event_info['event_timestmp']),
                'effectiveDate': convert_to_json_datetime(filing_obj.effective_date),
                'email': filing_event_info['email'],
                'name': filing_type
            }
            filing_obj.business = business

            return filing_obj

        except FilingNotFoundException as err:
            # pass through exception to caller
            raise err

        except Exception as err:
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))

            # pass through exception to caller
            raise err

    @classmethod
    def get_historic_filings(cls, business: Business = None):
        """Get list all filings from before the bob-date=2019-03-08."""
        if not business:
            return None

        try:
            historic_filings = []
            cursor = DB.connection.cursor()
            cursor.execute("""
                select event.event_id, event_timestmp, filing_typ_cd, effective_dt, period_end_dt, agm_date
                from event join filing on event.event_id = filing.event_id
                where corp_num=:identifier
                order by event_timestmp
                """,
                           identifier=business.get_corp_num()
                           )
            filings_info_list = []
            for filing_info in cursor:
                filings_info_list.append(dict(zip([x[0].lower() for x in cursor.description], filing_info)))
            for filing_info in filings_info_list:
                if not cls.FILING_TYPES[filing_info['filing_typ_cd']]:
                    raise InvalidFilingTypeException(filing_type=filing_info['filing_typ_cd'])
                filing_info['filing_type'] = cls.FILING_TYPES[filing_info['filing_typ_cd']]
                date = convert_to_json_date(filing_info['event_timestmp'])
                if date < '2019-03-08':
                    filing = Filing()
                    filing.business = business
                    filing.header = {
                        'date': date,
                        'name': filing_info['filing_type'],
                        'effectiveDate': convert_to_json_date(filing_info['effective_dt']),
                        'historic': True,
                        'availableOnPaperOnly': True
                    }
                    filing.body = {
                        filing_info['filing_type']: {
                            'eventId': filing_info['event_id'],
                            'annualReportDate': convert_to_json_date(filing_info['period_end_dt']),
                            'annualGeneralMeetingDate': convert_to_json_date(filing_info['agm_date'])
                        }
                    }
                    historic_filings.append(filing.as_dict())
            return historic_filings

        except InvalidFilingTypeException as err:
            current_app.logger.error('Unknown filing type found when getting historic filings for '
                                     f'{business.get_corp_num()}.')
            # pass through exception to caller
            raise err

        except Exception as err:
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))

            # pass through exception to caller
            raise err

    @classmethod
    def add_filing(cls, filing):  # pylint: disable=too-many-locals,too-many-statements,too-many-branches;
        """Add new filing to COLIN tables.

        :param filing: Filing dict.
        :returns (int): the filing ID of the new filing.
        """
        try:
            corp_num = filing.get_corp_num()
            user_id = 'COOPER' if corp_num[:2] == 'CP' else None
            # get db connection and start a session, in case we need to roll back
            con = DB.connection
            con.begin()
            cursor = con.cursor()

            # create new event record, return event ID
            event_id = cls._get_event_id(cursor, corp_num, 'FILE')

            # create new filing user
            cls._create_filing_user(cursor, event_id, filing, user_id)
            if filing.filing_type == 'annualReport':
                ar_date = filing.body['annualReportDate']
                agm_date = filing.body['annualGeneralMeetingDate']
                filing_type_cd = 'OTANN'

                # create new filing
                cls._create_filing(cursor, event_id, corp_num, ar_date, agm_date, filing_type_cd)

                # update corporation record
                Business.update_corporation(cursor, corp_num, agm_date)

                # update corp_state TO ACT (active) if it is in good standing. From CRUD:
                # - the current corp_state != 'ACT' and,
                # - they just filed the last outstanding ARs
                if filing.business.business['corpState'] != 'ACT':
                    agm_year = int(ar_date[:4])
                    last_year = datetime.datetime.now().year - 1
                    if agm_year >= last_year:
                        Business.update_corp_state(cursor, event_id, corp_num, state='ACT')

                # create new ledger text for annual report
                cls._add_ledger_text(
                    cursor=cursor, event_id=event_id, text=f'ANNUAL REPORT - {ar_date}', user_id=user_id)

            elif filing.filing_type == 'changeOfAddress':
                # set date to last ar date + 1 -- Bob wants this to be set to null
                # last_ar_date = filing.business.business['lastArDate']
                # day = int(last_ar_date[-2:]) + 1
                # try:
                #     date = str(datetime.datetime.strptime(last_ar_date[:-2] + ('0' + str(day))[1:], '%Y-%m-%d'))[:10]
                # except ValueError:
                #     try:
                #         day = '-01'
                #         month = int(last_ar_date[5:7]) + 1
                #         date = str(datetime.datetime.strptime(last_ar_date[:5] + ('0' + str(month))[1:] + day,
                #                                               '%Y-%m-%d')
                #                    )[:10]
                #     except ValueError:
                #         mm_dd = '-01-01'
                #         yyyy = int(last_ar_date[:4]) + 1
                #         date = str(datetime.datetime.strptime(str(yyyy) + mm_dd, '%Y-%m-%d'))[:10]
                date = None

                # create new filing
                filing_type_cd = 'OTADD'
                cls._create_filing(cursor, event_id, corp_num, date, None, filing_type_cd)

                # create new addresses for delivery + mailing, return address ids
                for office_type in filing.body['offices']:
                    office_arr = filing.body['offices'][office_type]
                    delivery_addr_id = Address.create_new_address(cursor, office_arr['deliveryAddress'])
                    mailing_addr_id = Address.create_new_address(cursor, office_arr['mailingAddress'])
                    office_desc = (office_type.replace('O', ' O')).title()
                    office_code = Office.OFFICE_TYPES_CODES[office_type]

                    # update office table to include new addresses
                    Office.update_office(cursor, event_id, corp_num, delivery_addr_id,
                                         mailing_addr_id, office_code)

                    # create new ledger text for address change
                    cls._add_ledger_text(cursor, event_id, f'Change to the {office_desc}.', user_id)
                # update corporation record
                Business.update_corporation(cursor, corp_num)

            elif filing.filing_type == 'changeOfDirectors':
                # create new filing
                # bob wants this to be null
                # date = filing.business.business['lastArDate']
                date = None
                filing_type_cd = 'OTCDR'
                cls._create_filing(cursor, event_id, corp_num, date, None, filing_type_cd)

                # create, cease, change directors
                changed_dirs = []
                for director in filing.body['directors']:
                    if 'appointed' in director['actions']:
                        Director.create_new_director(cursor=cursor, event_id=event_id, director=director,
                                                     business=filing.business.as_dict())

                    if 'ceased' in director['actions'] and not any(elem in ['nameChanged', 'addressChanged']
                                                                   for elem in director['actions']):
                        Director.end_by_name(cursor=cursor, director=director, event_id=event_id, corp_num=corp_num)

                    elif 'nameChanged' in director['actions'] or 'addressChanged' in director['actions']:
                        if 'appointed' in director['actions']:
                            current_app.logger.error(f'Director appointed with name/address change: {director}')
                        changed_dirs.append(director)
                        # end tmp copy of director with no cessation date (will be recreated with changes and cessation
                        # date - otherwise end up with two copies of ended director)
                        tmp = director.copy()
                        tmp['cessationDate'] = ''
                        Director.end_by_name(cursor=cursor, director=tmp, event_id=event_id, corp_num=corp_num)

                # add back changed directors as new row - if ceased director with changes this will add them with
                # cessation date + end event id filled
                for director in changed_dirs:
                    Director.create_new_director(cursor=cursor, event_id=event_id, director=director,
                                                 business=filing.business.as_dict())

                # create new ledger text for address change
                cls._add_ledger_text(cursor=cursor, event_id=event_id, text=f'Director change.', user_id=user_id)
                # update corporation record
                Business.update_corporation(cursor=cursor, corp_num=corp_num)

            else:
                raise InvalidFilingTypeException(filing_type=filing.filing_type)

            # success! commit the db changes
            con.commit()
            return event_id

        except Exception as err:
            # something went wrong, roll it all back
            current_app.logger.error(err.with_traceback(None))
            if con:
                con.rollback()

            raise err

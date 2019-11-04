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
from colin_api.models import Address, Business, Director, Office
from colin_api.resources.db import DB
from colin_api.utils import convert_to_json_date


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
        possible_filings = [Filing.FILING_TYPES[key] for key in Filing.FILING_TYPES]
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
                    INSERT INTO filing (event_id, filing_typ_cd, effective_dt, period_end_dt, agm_date)
                      VALUES (:event_id, :filing_type_code, sysdate, TO_DATE(:period_end_date, 'YYYY-mm-dd'),
                      TO_DATE(:agm_date, 'YYYY-mm-dd'))
                    """,
                               event_id=event_id,
                               filing_type_code=filing_type_code,
                               period_end_date=ar_date,
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
    def _create_filing_user(cls, cursor, event_id, filing):
        """Add to the FILING_USER table.

        :param cursor: oracle cursor
        :param event_id: (int) event_id for all events for this transaction
        :param filing: (obj) Filing data object
        """
        try:
            cursor.execute("""
                INSERT INTO filing_user (event_id, user_id, last_nme, first_nme, middle_nme, email_addr, party_typ_cd,
                role_typ_cd)
                  VALUES (:event_id, 'COOPER', :last_name, NULL, NULL, :email_address, NULL, NULL)
                """,
                           event_id=event_id,
                           last_name=filing.get_certified_by(),
                           email_address=filing.get_email()
                           )
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _add_ledger_text(cls, cursor, event_id, text):
        """Add note to ledger test table.

        :param cursor: oracle cursor
        :param event_id: (int) event id for corresponding event
        :param text: (str) note for ledger
        """
        try:
            cursor.execute("""
                INSERT INTO ledger_text (event_id, ledger_text_dts, notation, dd_event_id)
                  VALUES (:event_id, sysdate, :notation, :dd_event_id)
                """,
                           event_id=event_id,
                           notation=text,
                           dd_event_id=event_id
                           )
        except Exception as err:
            current_app.logger.error(f'Failed to add ledger text: "{text}" for event {event_id}')
            raise err

    @classmethod
    def _get_filing_event_info(cls,  # pylint: disable=too-many-arguments,too-many-branches;
                               identifier: str = None, event_id: str = None, filing_type_cd1: str = None,
                               filing_type_cd2: str = 'empty', year: int = None):

        # build base querystring
        querystring = ("""
                select event.event_id, event_timestmp, first_nme, middle_nme, last_nme, email_addr, period_end_dt,
                agm_date, effective_dt, event.corp_num
                from event
                join filing on filing.event_id = event.event_id
                left join filing_user on event.event_id = filing_user.event_id
                where (filing_typ_cd=:filing_type_cd1 or filing_typ_cd=:filing_type_cd2)
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
                                   filing_type_cd1=filing_type_cd1, filing_type_cd2=filing_type_cd2, year=year)
                else:
                    cursor.execute(querystring, identifier=identifier, event_id=event_id,
                                   filing_type_cd1=filing_type_cd1, filing_type_cd2=filing_type_cd2)
            else:
                if year:
                    cursor.execute(querystring, identifier=identifier, filing_type_cd1=filing_type_cd1,
                                   filing_type_cd2=filing_type_cd2, year=year)
                else:
                    cursor.execute(querystring, identifier=identifier, filing_type_cd1=filing_type_cd1,
                                   filing_type_cd2=filing_type_cd2)

            event_info = cursor.fetchone()

            if not event_info:
                raise FilingNotFoundException(identifier=identifier, filing_type=filing_type_cd1, event_id=event_id)

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
            return event_info

        except Exception as err:
            if identifier:
                current_app.logger.error('error getting filing event info for corp {}'.format(identifier))
            else:
                current_app.logger.error('error getting filing event info for event {}'.format(event_id))
            raise err

    @classmethod
    def _get_ar(cls, identifier: str = None, event_id: str = None,  # pylint: disable=too-many-locals,too-many-branches;
                year: int = None):
        """Return annual report filing."""
        if event_id:
            filing_event_info = cls._get_filing_event_info(identifier=identifier, event_id=event_id,
                                                           filing_type_cd1='OTANN', year=year)
        else:
            filing_event_info = cls._get_filing_event_info(identifier=identifier, filing_type_cd1='OTANN', year=year)

        if not filing_event_info:
            raise FilingNotFoundException(identifier=identifier, filing_type='annualReport', event_id=event_id)

        # get directors and registered office as of this filing
        director_events = Director.get_events(identifier=identifier)
        office_events = Office.get_events(identifier=identifier)
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

        if director_event_id:
            try:
                directors = Director.get_by_event(identifier=identifier, event_id=director_event_id)
            except:  # noqa B901; pylint: disable=bare-except;
                # should only get here if event was before the bob date
                directors = Director.get_current(identifier=identifier)
        else:
            directors = Director.get_current(identifier=identifier)
        directors = [x.as_dict() for x in directors]
        if office_event_id:
            try:
                reg_office = Office.get_by_event(event_id=office_event_id)
            except:  # noqa B901; pylint: disable=bare-except;
                # should only get here if event was before the bob date
                reg_office = Office.get_current(identifier=identifier)
        else:
            reg_office = Office.get_current(identifier=identifier)
        reg_office = reg_office.as_dict()
        # convert dates and date-times to correct json format
        filing_event_info['event_timestmp'] = convert_to_json_date(filing_event_info['event_timestmp'])
        agm_date = convert_to_json_date(filing_event_info.get('agm_date', None))
        ar_date = convert_to_json_date(filing_event_info['period_end_dt'])

        filing_obj = Filing()

        filing_obj.header = {
            'date': filing_event_info['event_timestmp'],
            'name': 'annualReport',
            'certifiedBy': filing_event_info['certifiedBy'],
            'email': filing_event_info['email']
        }
        filing_obj.body = {
            'annualGeneralMeetingDate': agm_date,
            'annualReportDate': ar_date,
            'directors': directors,
            'eventId': filing_event_info['event_id'],
            **reg_office
        }
        filing_obj.filing_type = 'annualReport'
        filing_obj.event_id = filing_event_info['event_id']  # pylint: disable=attribute-defined-outside-init

        return filing_obj

    @classmethod
    def _get_coa(cls, identifier: str = None, event_id: str = None,
                 year: int = None):  # pylint: disable=unused-argument; will use year later
        """Get change of address filing."""
        if event_id:
            filing_event_info = cls._get_filing_event_info(identifier=identifier, event_id=event_id,
                                                           filing_type_cd1='OTADD', filing_type_cd2='OTARG')
        else:
            filing_event_info = cls._get_filing_event_info(identifier=identifier, filing_type_cd1='OTADD',
                                                           filing_type_cd2='OTARG')

        registered_office_obj = Office.get_by_event(filing_event_info['event_id'])

        if not registered_office_obj:
            raise FilingNotFoundException(identifier=identifier, filing_type='change_of_address', event_id=event_id)

        filing_obj = Filing()
        filing_obj.header = {
            'date': convert_to_json_date(filing_event_info['event_timestmp']),
            'name': 'changeOfAddress',
            'certifiedBy': filing_event_info['certifiedBy'],
            'email': filing_event_info['email']
        }
        filing_obj.body = {
            **registered_office_obj.as_dict(),
            'eventId': filing_event_info['event_id']
        }
        filing_obj.filing_type = 'changeOfAddress'

        return filing_obj

    @classmethod
    def _get_cod(cls, identifier: str = None, event_id: str = None,
                 year: int = None):  # pylint: disable=unused-argument; will use year later
        """Get change of directors filing."""
        filing_obj = Filing()

        if event_id:
            filing_event_info = cls._get_filing_event_info(identifier=identifier, event_id=event_id,
                                                           filing_type_cd1='OTCDR', filing_type_cd2='OTADR')
        else:
            filing_event_info = cls._get_filing_event_info(identifier=identifier, filing_type_cd1='OTCDR',
                                                           filing_type_cd2='OTADR')

        director_objs = Director.get_by_event(identifier, filing_event_info['event_id'])
        if len(director_objs) < 3:
            current_app.logger.error('Less than 3 directors for {}'.format(identifier))

        filing_obj.header = {
            'date': convert_to_json_date(filing_event_info['event_timestmp']),
            'name': 'changeOfDirectors',
            'certifiedBy': filing_event_info['certifiedBy'],
            'email': filing_event_info['email']
        }

        filing_obj.body = {
            'directors': [x.as_dict() for x in director_objs],
            'eventId': filing_event_info['event_id']
        }
        filing_obj.filing_type = 'changeOfDirectors'

        return filing_obj

    @classmethod
    def get_filing(cls, business: Business = None, event_id: str = None, filing_type: str = None, year: int = None):
        """Get a Filing."""
        if not business or not filing_type:
            return None

        try:
            identifier = business.get_corp_num()

            if filing_type == 'annualReport':
                filing_obj = cls._get_ar(identifier=identifier, event_id=event_id, year=year)

            elif filing_type == 'changeOfAddress':
                filing_obj = cls._get_coa(identifier=identifier, event_id=event_id, year=year)

            elif filing_type == 'changeOfDirectors':
                filing_obj = cls._get_cod(identifier=identifier, event_id=event_id, year=year)

            else:
                raise InvalidFilingTypeException(filing_type=filing_type)

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
                if not Filing.FILING_TYPES[filing_info['filing_typ_cd']]:
                    raise InvalidFilingTypeException(filing_type=filing_info['filing_typ_cd'])
                filing_info['filing_type'] = Filing.FILING_TYPES[filing_info['filing_typ_cd']]
                date = convert_to_json_date(filing_info['event_timestmp'])
                if date < '2019-03-08':
                    filing = Filing()
                    filing.business = business
                    filing.header = {
                        'date': date,
                        'name': filing_info['filing_type'],
                        'availableOnPaperOnly': True
                    }
                    filing.body = {
                        filing_info['filing_type']: {
                            'eventId': filing_info['event_id'],
                            'eventDate': date,
                            'effectiveDate': convert_to_json_date(filing_info['effective_dt']),
                            'periodEndDate': convert_to_json_date(filing_info['period_end_dt']),
                            'agmDate': convert_to_json_date(filing_info['agm_date'])
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

            # get db connection and start a session, in case we need to roll back
            con = DB.connection
            con.begin()
            cursor = con.cursor()

            # create new event record, return event ID
            event_id = cls._get_event_id(cursor, corp_num, 'FILE')

            # create new filing user
            cls._create_filing_user(cursor, event_id, filing)
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

            elif filing.filing_type == 'changeOfAddress':
                # set date to last ar date + 1
                last_ar_date = filing.business.business['lastArDate']
                day = int(last_ar_date[-2:]) + 1
                try:
                    date = str(datetime.datetime.strptime(last_ar_date[:-2] + ('0' + str(day))[1:], '%Y-%m-%d'))[:10]
                except ValueError:
                    try:
                        day = '-01'
                        month = int(last_ar_date[5:7]) + 1
                        date = str(datetime.datetime.strptime(last_ar_date[:5] + ('0' + str(month))[1:] + day,
                                                              '%Y-%m-%d')
                                   )[:10]
                    except ValueError:
                        mm_dd = '-01-01'
                        yyyy = int(last_ar_date[:4]) + 1
                        date = str(datetime.datetime.strptime(str(yyyy) + mm_dd, '%Y-%m-%d'))[:10]

                # create new filing
                filing_type_cd = 'OTADD'
                cls._create_filing(cursor, event_id, corp_num, date, None, filing_type_cd)

                # create new addresses for delivery + mailing, return address ids
                for office in filing.body['offices']:
                    office_arr = filing.body['offices'][office]
                    delivery_addr_id = Address.create_new_address(cursor, office_arr['deliveryAddress'])
                    mailing_addr_id = Address.create_new_address(cursor, office_arr['mailingAddress'])
                    office_desc = Office.office_codes[office]['description']

                    # update office table to include new addresses
                    Office.update_office(cursor, event_id, corp_num, delivery_addr_id,
                                         mailing_addr_id, Office.office_codes[office]['code'])

                    # create new ledger text for address change
                    cls._add_ledger_text(cursor, event_id, f'Change to the {office_desc}, effective on {date}')
                # update corporation record
                Business.update_corporation(cursor, corp_num)

            elif filing.filing_type == 'changeOfDirectors':
                # create new filing
                date = filing.business.business['lastArDate']
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
                cls._add_ledger_text(cursor=cursor, event_id=event_id, text=f'Director change.')
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

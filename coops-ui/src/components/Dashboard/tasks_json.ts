// sample tasks JSON
// for use before mock is available
export default
{
    "tasks": [
        {
            filing: {
                "annualReport": {
                    "annualGeneralMeetingDate": "2018-07-15",
                    "certifiedBy": "full name",
                    "email": "no_one@never.get"
                },
                "changeOfDirectors": {
                    "certifiedBy": "full name",
                    "email": "no_one@never.get"
                },
                "changeOfAddress": {
                    "certifiedBy": "full name",
                    "email": "no_one@never.get"
                },
                "business": {
                    "cacheId": 1,
                    "foundingDate": "2007-04-08",
                    "identifier": "CP0002098",
                    "lastLedgerTimestamp": "2019-04-15T20:05:49.068272+00:00",
                    "legalName": "legal name - CP0002098"
                },
                "header": {
                    "date": "2017-06-06",
                    "filingId": 1,
                    "name": "annual_report",
                    "status": "DRAFT"
                }
            }
        },
        {
            filing: {
                "todoItem": {
                    "name": "annual_report",
                    "ARFilingYear": 2019
                },
                "business": {
                    "cacheId": 1,
                    "foundingDate": "2007-04-08",
                    "identifier": "CP0002098",
                    "lastLedgerTimestamp": "2019-04-15T20:05:49.068272+00:00",
                    "legalName": "legal name - CP0002098"
                },
                "header": {
                    "date": "2019-07-15",
                    "filingId": 2,
                    "name": "todo_item",
                    "status": "NEW"
                }
            }
        },
        {
            filing:  {
                "changeOfDirectors": {
                    "certifiedBy": "full name",
                    "email": "no_one@never.get"
                },
                "business": {
                    "cacheId": 1,
                    "foundingDate": "2007-04-08",
                    "identifier": "CP0002098",
                    "lastLedgerTimestamp": "2019-04-15T20:05:49.068272+00:00",
                    "legalName": "legal name - CP0002098"
                },
                "header": {
                    "date": "2016-06-06",
                    "filingId": 3,
                    "name": "change_of_directors",
                    "paymentToken": "token",
                    "status": "PENDING"
                }
            }
        },
        {
            filing:  {
                "changeOfAddress": {
                    "certifiedBy": "full name",
                    "email": "no_one@never.get"
                },
                "business": {
                    "cacheId": 1,
                    "foundingDate": "2007-04-08",
                    "identifier": "CP0002098",
                    "lastLedgerTimestamp": "2019-04-15T20:05:49.068272+00:00",
                    "legalName": "legal name - CP0002098"
                },
                "header": {
                    "date": "2016-06-06",
                    "filingId": 4,
                    "name": "change_of_address",
                    "paymentToken": "token",
                    "status": "ERROR"
                }
            }
        }
    ]
}

// sample tasks JSON
// for use before mock is available
export default
{
    "tasks": [
        {
            "filing": {
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
            },
            "order": 1,
            "enabled": true
        },
        {
            "todo": {
                "business": {
                    "cacheId": 1,
                    "foundingDate": "2007-04-08",
                    "identifier": "CP0002098",
                    "lastLedgerTimestamp": "2019-04-15T20:05:49.068272+00:00",
                    "legalName": "legal name - CP0002098"
                },
                "header": {
                    "name": "annual_report",
                    "ARFilingYear": 2019,
                    "status": "NEW"
                }
            },
            "order": 2,
            "enabled": false
        },
        {
            "filing":  {
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
            },
            "order": 3,
            "enabled": false
        },
        {
            "filing":  {
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
            },
            "order": 4,
            "enabled": false
        }
    ]
}

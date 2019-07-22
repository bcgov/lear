// sample tasks JSON
// for use before mock is available
export default
{
    "tasks": [
        {
            "todo": {
                "business": {
                    "cacheId": 1,
                    "foundingDate": "2007-04-08",
                    "identifier": "CP0002098",
                    "lastLedgerTimestamp": "2019-04-15T20:05:49.068272+00:00",
                    "legalName": "Legal Name - CP0002098"
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
            "filing": {
                "annualReport": {
                    "annualGeneralMeetingDate": "2018-07-15",
                    "certifiedBy": "full1 name1",
                    "email": "no_one1@never.get"
                },
                "changeOfDirectors": {
                    "certifiedBy": "full2 name2",
                    "email": "no_one2@never.get"
                },
                "changeOfAddress": {
                    "certifiedBy": "full3 name3",
                    "email": "no_one3@never.get"
                },
                "business": {
                    "cacheId": 1,
                    "foundingDate": "2007-04-08",
                    "identifier": "CP0002098",
                    "lastLedgerTimestamp": "2019-04-15T20:05:49.068272+00:00",
                    "legalName": "Legal Name - CP0002098"
                },
                "header": {
                    "date": "2017-06-06",
                    "filingId": 102,
                    "name": "annual_report",
                    "status": "DRAFT"
                }
            },
            "order": 1,
            "enabled": true
        },
        {
            "filing":  {
                "changeOfDirectors": {
                    "certifiedBy": "full4 name4",
                    "email": "no_one4@never.get"
                },
                "business": {
                    "cacheId": 1,
                    "foundingDate": "2007-04-08",
                    "identifier": "CP0002098",
                    "lastLedgerTimestamp": "2019-04-15T20:05:49.068272+00:00",
                    "legalName": "Legal Name - CP0002098"
                },
                "header": {
                    "date": "2016-06-06",
                    "filingId": 101,
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
                    "certifiedBy": "full5 name5",
                    "email": "no_one5@never.get"
                },
                "business": {
                    "cacheId": 1,
                    "foundingDate": "2007-04-08",
                    "identifier": "CP0002098",
                    "lastLedgerTimestamp": "2019-04-15T20:05:49.068272+00:00",
                    "legalName": "Legal Name - CP0002098"
                },
                "header": {
                    "date": "2016-06-06",
                    "filingId": 100,
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

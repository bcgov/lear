// sample tasks JSON
// for use before mock is available
export default
{
  'tasks': [
    {
      'task': {
        'todo': {
          'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP0002098',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': 'Legal Name - CP0002098'
          },
          'header': {
            'name': 'annual_report',
            'ARFilingYear': 2019,
            'status': 'NEW'
          }
        }
      },
      'order': 2,
      'enabled': false
    },
    {
      'task': {
        'filing': {
          'annualReport': {
            'annualGeneralMeetingDate': '2018-07-15',
            'certifiedBy': 'full1 name1',
            'email': 'no_one@never.get'
          },
          'changeOfAddress': {
            'certifiedBy': 'full2 name2',
            'email': 'no_one@never.get'
          },
          'changeOfDirectors': {
            'certifiedBy': 'full3 name3',
            'email': 'no_one@never.get'
          },
          'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP0002098',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': 'Legal Name - CP0002098'
          },
          'header': {
            'date': '2017-06-06',
            'filingId': 123,
            'name': 'annual_report',
            'status': 'DRAFT'
          }
        }
      },
      'order': 1,
      'enabled': true
    },
    {
      'task': {
        'filing': {
          'changeOfAddress': {
            'certifiedBy': 'full2 name2',
            'email': 'no_one@never.get'
          },
          'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP0002098',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': 'Legal Name - CP0002098'
          },
          'header': {
            'date': '2017-06-06',
            'filingId': 456,
            'name': 'change_of_address',
            'status': 'ERROR'
          }
        }
      },
      'order': 4,
      'enabled': false
    },
    {
      'task': {
        'filing': {
          'changeOfDirectors': {
            'certifiedBy': 'full3 name3',
            'email': 'no_one@never.get'
          },
          'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP0002098',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': 'Legal Name - CP0002098'
          },
          'header': {
            'date': '2017-06-06',
            'filingId': 789,
            'name': 'change_of_directors',
            'status': 'PENDING'
          }
        }
      },
      'order': 3,
      'enabled': false
    }
  ]
}

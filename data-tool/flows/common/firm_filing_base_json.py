
def get_base_sp_registration_json(num_parties: int):
    registration_json = get_base_registration_json()
    parties = registration_json['filing']['registration']['parties']
    for x in range(num_parties):
        parties.append(get_base_party_json())
    return registration_json


def get_base_registration_json():
    registration_json = {
        'filing': {
            'header': {
                'date': None,
                'name': 'registration',
                'certifiedBy': None,
                'folioNumber': '',
                'isFutureEffective': False
            },
            'business': {
                'legalType': None,
                'identifier': None,
                'foundingDate': None
            },
            'registration': {
                'offices': {
                    'businessOffice': {
                        'mailingAddress': {
                            'postalCode': None,
                            'addressCity': None,
                            'addressRegion': None,
                            'streetAddress': None,
                            'addressCountry': None,
                            'streetAddressAdditional': None,
                            'deliveryInstructions': None
                        },
                        'deliveryAddress': {
                            'postalCode': None,
                            'addressCity': None,
                            'addressRegion': None,
                            'streetAddress': None,
                            'addressCountry': None,
                            'streetAddressAdditional': None,
                            'deliveryInstructions': None
                        }
                    }
                },
                'parties': [],
                'business': {
                    'naics': {
                        'naicsCode': None,
                        'naicsDescription': None
                    },
                    'identifier': None
                },
                'startDate': None,
                'nameRequest': {
                    'nrNumber': None,
                    'legalName': None,
                    'legalType': None
                },
                'businessType': None,
                'contactPoint': {
                    'email': None,
                    'phone': None
                }
            }
        }
    }
    return registration_json


def get_base_party_json():
    party_json = {
            'roles': [
                {
                    'roleType': None
                }
            ],
            'officer': {
                'email': None,
                'lastName': None,
                'firstName': None,
                'partyType': None,
                'middleName': None,
                'organizationName': None,
                'identifier': None
            },
            'mailingAddress': {
                'postalCode': None,
                'addressCity': None,
                'addressRegion': None,
                'streetAddress': None,
                'addressCountry': None,
                'streetAddressAdditional': None
            },
            'deliveryAddress': {
                'postalCode': None,
                'addressCity': None,
                'addressRegion': None,
                'streetAddress': None,
                'addressCountry': None,
                'streetAddressAdditional': None,
                'deliveryInstructions': None
            }
        }
    return party_json

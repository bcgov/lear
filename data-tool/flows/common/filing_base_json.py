
def get_base_registration_filing_json(num_parties: int):
    registration_json = get_base_registration_json()
    parties = registration_json['filing']['registration']['parties']
    for x in range(num_parties):
        parties.append(get_base_party_json())
    return registration_json


def get_base_change_registration_filing_json(num_parties: int):
    change_registration_json = get_base_change_registration_json()
    parties = change_registration_json['filing']['changeOfRegistration']['parties']
    for x in range(num_parties):
        parties.append(get_base_party_json())
    return change_registration_json


def get_base_correction_filing_json(num_parties: int):
    correction_json = get_base_correction_json()
    parties = correction_json['filing']['correction']['parties']
    for _ in range(num_parties):
        parties.append(get_base_party_json())
    return correction_json


def get_base_dissolution_filing_json(dissolution_type: str):
    if dissolution_type != 'voluntary':
        return None

    dissolution_json = get_base_dissolution_json(dissolution_type)
    parties = dissolution_json['filing']['dissolution']['parties']
    # add a base party for completing party
    parties.append(get_base_party_json())
    return dissolution_json


def get_base_conversion_filing_json(num_parties: int):
    conversion_json = get_base_conversion_json()
    parties = conversion_json['filing']['conversion']['parties']
    for idx in range(num_parties):
        parties.append(get_base_party_json())
    return conversion_json


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
                    'identifier': None,
                    "taxId": None,
                },
                'startDate': None,
                'nameRequest': {
                    'nrNumber': None,
                    'legalName': None,
                    'legalType': None
                },
                'businessType': None,
                'contactPoint': {
                    'email': None
                }
            }
        }
    }
    return registration_json


def get_base_change_registration_json():
    change_registration_json = {
        'filing': {
            'header': {
                'date': None,
                'name': 'changeOfRegistration',
                'certifiedBy': None,
                'folioNumber': '',
                'isFutureEffective': False
            },
            'business': {
                'legalType': None,
                'identifier': None,
                'foundingDate': None
            },
            'changeOfRegistration': {
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
                'nameRequest': {
                    'nrNumber': None,
                    'legalName': None,
                    'legalType': None
                },
                'contactPoint': {
                    'email': None
                }
            }
        }
    }
    return change_registration_json


def get_base_correction_json():
    correction_json = {
        'filing': {
            'header': {
                'date': None,
                'name': 'correction',
                'certifiedBy': None,
                'folioNumber': ''
            },
            'business': {
                'legalName': None,
                'legalType': None,
                'identifier': None
            },
            'correction': {
                'type': None,
                'comment': None,
                'correctedFilingId': None,
                'correctedFilingDate': None,
                'correctedFilingType': None,
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
                'contactPoint': {
                    'email': None
                }
            }
        }
    }
    return correction_json


def get_base_dissolution_json(dissolution_type: str):
    dissolution_json = {
        'filing': {
            'header': {
                'date': None,
                'name': 'dissolution',
                'certifiedBy': None,
                'isFutureEffective': False
            },
            'business': {
                'legalName': None,
                'legalType': None,
                'identifier': None,
                'foundingDate': None
            },
            'dissolution': {
                'parties': [],
                'custodialOffice': None,
                'dissolutionDate': None,
                'dissolutionType': dissolution_type
            }
        }
    }
    return dissolution_json


def get_base_conversion_json():
    conversion_json = {
        'filing': {
            'header': {
                'date': None,
                'name': 'conversion',
                'certifiedBy': None,
                'folioNumber': '',
                'isFutureEffective': False
            },
            'business': {
                'legalType': None,
                'identifier': None,
                'foundingDate': None
            },
            'conversion': {
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
                        'naicsDescription': None
                    },
                    'identifier': None,
                    "natureOfBusiness": ""
                },
                'nameRequest': {
                    'nrNumber': None,
                    'legalName': None,
                    'legalType': None
                },
                'startDate': None,
                'contactPoint': {
                    'email': None
                }
            }
        }
    }
    return conversion_json


def get_base_put_back_on_filing_json():
    put_back_on_json = get_base_put_back_on_json()
    return put_back_on_json


def get_base_put_back_on_json():
    put_back_on_json = {
        'filing': {
            'header': {
                'date': None,
                'name': 'putBackOn',
                'certifiedBy': None,
                'isFutureEffective': False
            },
            'business': {
                'legalName': None,
                'legalType': None,
                'identifier': None,
                'foundingDate': None
            },
            "putBackOn": {
                "details": None
            }
        }
    }
    return put_back_on_json


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

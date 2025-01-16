
def get_base_ia_filing_json(num_parties: int, num_corp_names = 0, num_share_classes = 0):
    ia_json = get_base_ia_json()

    parties = ia_json['filing']['incorporationApplication']['parties']
    for x in range(num_parties):
        parties.append(get_base_party_json())

    name_translations = ia_json['filing']['incorporationApplication']['nameTranslations']
    for x in range(num_corp_names):
        name_translations.append(get_base_name_translation_json())

    share_classes = ia_json['filing']['incorporationApplication']['shareStructure']['shareClasses']
    for x in range(num_share_classes):
        share_classes.append(get_base_share_class_json())

    return ia_json


def get_base_ar_filing_json(num_directors: int):
    ar_json = get_base_ar_json()

    directors = ar_json['filing']['annualReport']['directors']
    for _ in range(num_directors):
        directors.append(get_base_director_json())

    return ar_json


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


def get_base_continuation_in_filing_json(num_parties: int, num_corp_names = 0, num_share_classes = 0):
    continuation_in_json = get_base_continuation_in_json()

    parties = continuation_in_json['filing']['continuationIn']['parties']
    for x in range(num_parties):
        parties.append(get_base_party_json())

    name_translations = continuation_in_json['filing']['continuationIn']['nameTranslations']
    for x in range(num_corp_names):
        name_translations.append(get_base_name_translation_json())

    share_classes = continuation_in_json['filing']['continuationIn']['shareStructure']['shareClasses']
    for x in range(num_share_classes):
        share_classes.append(get_base_share_class_json())

    return continuation_in_json


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


def get_base_ia_json():
    ia_json = {
        'filing': {
            'header': {
                'date': None,
                'name': 'incorporationApplication',
                'certifiedBy': None,
                'folioNumber': '',
                'isFutureEffective': False
            },
            'business': {
                'legalType': None,
                'identifier': None,
                'foundingDate': None
            },
            'incorporationApplication': {
                'offices': {
                    'recordsOffice': {
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
                    },
                    'registeredOffice': {
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
                'nameRequest': {
                    'nrNumber': None,
                    'legalName': None,
                    'legalType': None
                },
                'contactPoint': {
                    'email': None
                },
                'shareStructure': {
                    'shareClasses': []
                },
                'nameTranslations': [],
                'incorporationAgreement': {
                    'agreementType': None
                },
                'courtOrder': {
                    'fileNumber': None,
                    'effectOfOrder': None,
                    'hasPlanOfArrangement': False
                }
            }
        }
    }
    return ia_json

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


def get_base_continuation_in_json():
    continuation_in_json = {
        'filing': {
            'header': {
                'date': None,
                'name': 'continuationIn',
                'certifiedBy': None,
                'folioNumber': '',
                'isFutureEffective': False
            },
            'business': {
                'legalType': None,
                'identifier': None,
                'foundingDate': None
            },
            'continuationIn': {
                'business': {  # expro data in BC
                    "foundingDate": None,
                    "identifier": None,
                    "legalName": None
                },
                'offices': {
                    'recordsOffice': {
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
                    },
                    'registeredOffice': {
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
                'nameRequest': {
                    'nrNumber': None,
                    'legalName': None,
                    'legalType': None
                },
                'contactPoint': {
                    'email': None
                },
                'shareStructure': {
                    'shareClasses': []
                },
                'nameTranslations': [],
                'foreignJurisdiction': {
                    "country": None,
                    "region": None,
                    "legalName": None,
                    "identifier": None,
                    "incorporationDate":None
                },
                'courtOrder': {
                    'fileNumber': None,
                    'effectOfOrder': None,
                    'hasPlanOfArrangement': False
                }
            }
        }
    }
    return continuation_in_json


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


def get_base_name_translation_json():
    name_translation_json = {
        'name': None,
        'type': None
    }
    return name_translation_json


def get_base_share_class_json():
    share_class_json = {
        'name': None,
        'type': 'Class',
        'series': [],
        'currency': None,
        'parValue': None,
        'priority': None,
        'hasParValue': None,
        'hasMaximumShares': None,
        'maxNumberOfShares': None,
        'hasRightsOrRestrictions': False
    }
    return share_class_json


def get_base_share_series_json():
    share_series_json = {
        'name': None,
        'type': 'Series',
        'currency': None,
        'parValue': None,
        'priority': None,
        'hasParValue': None,
        'hasMaximumShares': None,
        'maxNumberOfShares': None,
        'hasRightsOrRestrictions': None
    }
    return share_series_json


def get_base_ar_json():
    ar_json = {
        'filing': {
            'header': {
                'date': None,
                'name': 'annualReport',
                'email': None,
                'certifiedBy': None,
                'ARFilingYear': None,
                'effectiveDate': None
            },
            'business': {
                'legalName': None,
                'legalType': None,
                'identifier': None,
                'foundingDate': None
            },
            'annualReport': {
                'offices': {
                    'recordsOffice': {
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
                    },
                    'registeredOffice': {
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
                'directors': [],
                'nextARDate': None,
                'annualReportDate': None
            }
        }
    }
    return ar_json


def get_base_director_json():
    director_json = {
        'role': 'director',
        'appointmentDate': None,
        'cessationDate': None,
        'officer': {
            "id": None,
            "email": None,
            "lastName": None,
            "firstName": None,
            "partyType": "person",
            "prevLastName": None,
            "middleInitial": None,
            "prevFirstName": None,
            "prevMiddleInitial": None
        },
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
    return director_json

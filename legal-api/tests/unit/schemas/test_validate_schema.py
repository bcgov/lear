
from legal_api.schemas import validate_schema


def test_validate_schema_fail_empty():
    data = {}
    valid, errors = validate_schema(data, 'business.json')

    for error in errors:
        print('Error:', error.message)
        for suberror in sorted(error.context, key=lambda e: e.schema_path):
            print('Schema Errors', list(suberror.schema_path), suberror.message, sep=", ")

    assert not valid


def test_validate_schema_pass_business_info_data():
    data = {
        "business": {
            "last_ledger_timestamp": "2019-04-16T00:00:00+00:00",
            "founding_date": "2019-04-08",
            "identifier": "CP1234567",
            "legal_name": "legal name"
        },
    }
    valid, errors = validate_schema(data, 'business.json')

    if errors:
        for error in errors:
            print('listing errors')
            print('Error:', error.message, 'context', error.context)
            for suberror in sorted(error.context, key=lambda e: e.schema_path):
                print('Schema Errors', list(suberror.schema_path), suberror.message, sep=", ")

    assert valid

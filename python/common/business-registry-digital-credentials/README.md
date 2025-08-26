# Business Registry Digital Credentials

This library includes components used for Digital Business Card functionality. It accesses the data model for DBC tables/etc, and makes external calls to the Traction API as well as other utilities like permission checks.

## Environment variables

Env vars used by these modules should be definied in the calling service that imports them (IE the `business-api` or the `business-digital-credentials` queue-service) so see sample env files in appropriate projects.

Basic common database connection env vars are used, as this uses `business-model`, as well as various `TRACTION_*`, `BUSINESS_SCHEMA/CRED_DEF_*`, and `WALLET_*` env vars. 

## Poetry & lint/test
```shell
poetry install
```

### Linting
Check code style with flake8
```shell
poetry run flake8 src/business_registry_digital_credentials
```

Check code formatting with black (without changing files)
```shell
poetry run black --check src/business_registry_digital_credentials tests
```

# Check import sorting with isort (without changing files)
```shell
poetry run isort --check-only src/business_registry_digital_credentials tests
```

Can remove the --check or --check-only flags to auto-fix

### Testing
```shell
poetry run pytest
```

## 🛠️ TODO

- In digital_credentials_utils handle flag usage before business-api needs to call this code.
- Import and fix futher unit tests from business-api.

---
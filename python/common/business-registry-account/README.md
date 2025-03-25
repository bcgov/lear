



# Business Registry Dissolution

This library provides the dissolution service, previously available as part of the legal api

## Required env values to use
AUTH_SVC_URL
ACCOUNT_SVC_AUTH_URL
ACCOUNT_SVC_CLIENT_ID
ACCOUNT_SVC_CLIENT_SECRET
JWT_OIDC_WELL_KNOWN_CONFIG
JWT_OIDC_ALGORITHMS
JWT_OIDC_JWKS_URI
JWT_OIDC_ISSUER
JWT_OIDC_AUDIENCE
JWT_OIDC_CLIENT_SECRET
JWT_OIDC_CACHING_ENABLED
JWT_OIDC_USERNAME
JWT_OIDC_FIRSTNAME
JWT_OIDC_LASTNAME
JWT_OIDC_JWKS_CACHE_TIMEOUT
ACCOUNT_SVC_TIMEOUT

## Technology Stack Used
* Python3
* Flask-SQLAlchemy & alembic
* Postgres


## Poetry
You may prefer to have the vitrual-environment in the project home. To do that, tell poetry to use a local .venv before installing.
```shell
poetry config virtualenvs.in-project true
```
```shell
poetry install
```

You can issue any command in the current environment, via poetry's shell
```shell
poetry shell
```

### Aside: faster local dev?
change the git installed services to the local versions and rebuild the lockfile
```bash
poetry lock
```
remember to switch them back before the final PR

## Tests
pytest
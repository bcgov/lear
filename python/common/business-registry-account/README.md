



# Business Registry Dissolution

This library provides the dissolution service, previously available as part of the legal api

## Required env values to use
AUTH_SVC_URL
ACCOUNT_SVC_AUTH_URL
ACCOUNT_SVC_CLIENT_ID
ACCOUNT_SVC_CLIENT_SECRET

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
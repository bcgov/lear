




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

## Database management
via poetry's shell, or enabling a python virtualenv  
Using the Flask db commands can be used
Deploy to a configured database
```shell
flask db upgrade
```
Update migrations for model changes
```shell
flask db migrate
```

## Tests
pytest
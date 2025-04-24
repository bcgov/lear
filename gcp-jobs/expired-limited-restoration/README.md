# Expired Limited Restoration

Expired Limited Restoration GCP Job

## Development Environment

Follow the instructions of the [Development Readme](https://github.com/bcgov/entity/blob/master/docs/development.md)
to setup your local development environment.

## Development Setup

1. Follow the [instructions](https://github.com/bcgov/entity/blob/master/docs/setup-forking-workflow.md) to checkout the
   project from GitHub.
2. Open the Expired Limited Restoration directory in VS Code to treat it as a project (or WSL projec). To prevent version
   clashes,
   set up a virtual environment to install the Python packages used by this project.

## Poetry

You may prefer to have the vitrual-environment in the project home. To do that, tell poetry to use a local .venv before
installing.

```shell
poetry config virtualenvs.in-project true
```

```shell
poetry install
```

You can issue any command in the current environment, via poetry's shell

```shell
source $(poetry env activate)
```

### Run the job

```bash
python run.py
```

### Run Linting

```bash
ruff check
```

### Run unit tests

```
pytest
```


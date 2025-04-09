# Future Effective Filings Report

Generate notebook report

## Development Environment

Follow the instructions of the [Development Readme](https://github.com/bcgov/entity/blob/master/docs/development.md)
to setup your local development environment.

## Development Setup

1. Follow the [instructions](https://github.com/bcgov/entity/blob/master/docs/setup-forking-workflow.md) to checkout the project from GitHub.
2. Open the notebook-report directory in VS Code to treat it as a project (or WSL projec). To prevent version clashes, set up a virtual environment to install the Python packages used by this project.
3. Run `make setup` to set up the virtual environment and install libraries.

## Running Notebook Report

1. Run `. venv/bin/activate` to change to `venv` environment.
2. Run notebook with `python notebookreport.py`

## Running Unit Tests

1. Run `python -m pytest` or `pytest` command.

## NOTE ABOUT REQS
This job is on python 3.12 instead of 3.13 because spacy won't work as of the time of writing on python 3.13

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



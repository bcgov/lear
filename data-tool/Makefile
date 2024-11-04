.PHONY: license
.PHONY: setup
.PHONY: run

# Get the absolute path of the Makefile's directory
MKFILE_PATH:=$(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_ABS_DIR:=$(patsubst %/,%,$(dir $(MKFILE_PATH)))

PROJECT_NAME:=legal_api
DOCKER_NAME:=legal-api

# Virtual environment variables
VENV_DIR=venv
PREFECT_VENV_DIR=venv-prefect
SQLALCHEMY_VENV_DIR=venv-sqlalchemy
PYTHON_VERSION=python3.11

#################################################################################
# COMMANDS -- Setup                                                             #
#################################################################################
setup: install-all ## Setup all virtual environments

clean: clean-build clean-pyc clean-test clean-venv ## Clean everything

clean-venv: ## Clean virtual environments
	rm -rf $(VENV_DIR)/
	rm -rf $(PREFECT_VENV_DIR)/
	rm -rf $(SQLALCHEMY_VENV_DIR)/

clean-build: ## Clean build files
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +

clean-pyc: ## Clean cache files
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## clean test files
	find . -name '.pytest_cache' -exec rm -fr {} +
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

install-all: clean install-prefect install-sqlalchemy install ## Install all virtual environments

install-prefect: ## Install prefect server environment
	test -f $(PREFECT_VENV_DIR)/bin/activate || $(PYTHON_VERSION) -m venv $(PREFECT_VENV_DIR) ;\
	. $(PREFECT_VENV_DIR)/bin/activate ;\
	pip install --upgrade pip ;\
	pip install -r requirements/prefect.txt

install-sqlalchemy: ## Install SQLAlchemy 1.4.44 environment
	test -f $(SQLALCHEMY_VENV_DIR)/bin/activate || $(PYTHON_VERSION) -m venv $(SQLALCHEMY_VENV_DIR) ;\
	. $(SQLALCHEMY_VENV_DIR)/bin/activate ;\
	pip install --upgrade pip ;\
	pip install "SQLAlchemy==1.4.44"

install: clean ## Install main application environment
	test -f $(VENV_DIR)/bin/activate || $(PYTHON_VERSION) -m venv $(VENV_DIR) ;\
	. $(VENV_DIR)/bin/activate ;\
	pip install --upgrade pip ;\
	pip install -r requirements.txt ;\
	pip install --no-deps git+https://github.com/bcgov/lear.git#egg=legal_api\&subdirectory=legal-api ;\
	pip install --no-deps git+https://github.com/bcgov/business-schemas.git@2.16.1#egg=registry_schemas ;\
	pip install --no-deps git+https://github.com/bcgov/lear.git#egg=sql-versioning\&subdirectory=python/common/sql-versioning

build-req: clean ## Upgrade requirements
	test -f $(VENV_DIR)/bin/activate || $(PYTHON_VERSION) -m venv  $(CURRENT_ABS_DIR)/$(VENV_DIR) ;\
	. $(VENV_DIR)/bin/activate ;\
	pip install --upgrade pip ;\
	pip install -Ur requirements/prod.txt ;\
	pip freeze | sort > requirements.txt ;\
	cat requirements/bcregistry-libraries.txt >> requirements.txt ;\
	pip install -Ur requirements/bcregistry-libraries.txt


#################################################################################
# COMMANDS - Local                                                              #
#################################################################################
run-prefect-server: ## Start Prefect server
	. $(PREFECT_VENV_DIR)/bin/activate && prefect server start

run-prefect-reset-db: ## clears all data and reapplies the schema.  Handy for clearing flow run history.
	. $(PREFECT_VENV_DIR)/bin/activate && prefect server database reset -y

run-corps-migration: ## Run migration flow
	@echo "Current directory: $(CURRENT_ABS_DIR)"
	@echo "SQLAlchemy path: $(CURRENT_ABS_DIR)/$(SQLALCHEMY_VENV_DIR)/lib/$(PYTHON_VERSION)/site-packages"
	. $(VENV_DIR)/bin/activate && \
	export PYTHONPATH="$(CURRENT_ABS_DIR):$$PYTHONPATH" && \
	export SQLALCHEMY_PATH="$(CURRENT_ABS_DIR)/$(SQLALCHEMY_VENV_DIR)/lib/$(PYTHON_VERSION)/site-packages" && \
	FLASK_ENV=development && \
	python flows/migrate_corps_flow.py

run-corps-delete: ## Run delete flow
	. $(VENV_DIR)/bin/activate && \
	python flows/batch_delete_flow.py


#################################################################################
# Self Documenting Commands                                                     #
#################################################################################
.PHONY: help

.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

debug-path:
	@echo "MKFILE_PATH: $(MKFILE_PATH)"
	@echo "CURRENT_ABS_DIR: $(CURRENT_ABS_DIR)"

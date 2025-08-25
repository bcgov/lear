.PHONY: license
.PHONY: setup
.PHONY: ci cd
.PHONY: run

MKFILE_PATH:=$(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_ABS_DIR:=$(patsubst %/,%,$(dir $(MKFILE_PATH)))

PROJECT_NAME:=legal_api
DOCKER_NAME:=legal-api

#################################################################################
# COMMANDS -- Setup                                                             #
#################################################################################
setup: install  ## Setup the project

clean: clean-build clean-pyc clean-test ## Clean the project
	rm -rf venv/

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

install: clean ## Install python virtual environment
	poetry install --all-extras

#################################################################################
# COMMANDS - CI                                                                 #
#################################################################################
ci: lint flake8 test ## CI flow

pylint: ## Linting with pylint
	@. venv/bin/activate; \
	PYLINT_VERSION=$$(pylint --version 2>&1 | grep -oP 'pylint \K(\d+\.\d+)'); \
	if [ "$$PYLINT_VERSION" \> "3.3" ] || [ "$$PYLINT_VERSION" = "3.3" ]; then \
		echo ". venv/bin/activate && pylint --rcfile=setup.cfg --load-plugins=pylint_flask --disable=too-many-positional-arguments src/$(PROJECT_NAME)";\
		pylint --rcfile=setup.cfg --load-plugins=pylint_flask --disable=too-many-positional-arguments src/$(PROJECT_NAME); \
	else \
		echo ". venv/bin/activate && pylint --rcfile=setup.cfg --load-plugins=pylint_flask src/$(PROJECT_NAME)";\
		pylint --rcfile=setup.cfg --load-plugins=pylint_flask src/$(PROJECT_NAME); \
	fi

flake8: ## Linting with flake8
	. venv/bin/activate && flake8 src/$(PROJECT_NAME)

lint: pylint flake8 ## run all lint type scripts

test: ## Unit testing
	. venv/bin/activate && pytest

mac-cov: test ## Run the coverage report and display in a browser window (mac)
	@open -a "Google Chrome" htmlcov/index.html

#################################################################################
# COMMANDS - CD
# expects the terminal to be openshift login
# expects export OPENSHIFT_DOCKER_REGISTRY=""
# expects export OPENSHIFT_SA_NAME="$(oc whoami)"
# expects export OPENSHIFT_SA_TOKEN="$(oc whoami -t)"
# expects export OPENSHIFT_REPOSITORY=""
# expects export TAG_NAME="dev/test/prod"
# expects export OPS_REPOSITORY=""                                                        #
#################################################################################
cd: ## CD flow
ifeq ($(TAG_NAME), test)
# cd: update-env
cd:
	oc -n "$(OPENSHIFT_REPOSITORY)-tools" tag $(DOCKER_NAME):dev $(DOCKER_NAME):$(TAG_NAME)
else ifeq ($(TAG_NAME), prod)
# cd: update-env
cd:
	oc -n "$(OPENSHIFT_REPOSITORY)-tools" tag $(DOCKER_NAME):$(TAG_NAME) $(DOCKER_NAME):$(TAG_NAME)-$(shell date +%F)
	oc -n "$(OPENSHIFT_REPOSITORY)-tools" tag $(DOCKER_NAME):test $(DOCKER_NAME):$(TAG_NAME)
else
TAG_NAME=dev
# cd: build update-env tag
cd: build tag
endif

build: ## Build the docker container
	docker build . -t $(DOCKER_NAME) \
		-f Dockerfile \
		--platform linux/amd64 \
		--build-arg VCS_REF=$(shell git rev-parse --short HEAD) \
		--build-arg BUILD_DATE=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

build-nc: ## Build the docker container without caching
	docker build --no-cache -t $(DOCKER_NAME) -f Dockerfile-ocp .

# 1Password CLI1 will be deprecated on Oct 1, 2024
# VAULTS=`cat devops/vaults.json`
# update-env: ## Update env from 1pass
# 	oc -n "$(OPS_REPOSITORY)-$(TAG_NAME)" exec "dc/vault-service-$(TAG_NAME)" -- ./scripts/1pass.sh \
# 		-m "secret" \
# 		-e "$(TAG_NAME)" \
# 		-a "$(DOCKER_NAME)-$(TAG_NAME)" \
# 		-n "$(OPENSHIFT_REPOSITORY)-$(TAG_NAME)" \
# 		-v "$(VAULTS)" \
# 		-r "true" \
# 		-f "false"

#################################################################################
# COMMANDS - Local                                                              #
#################################################################################
run: ## Run the project in local
	. .venv/bin/activate && python -m flask run -p 5000

#################################################################################
# Self Documenting Commands                                                     #
#################################################################################
.PHONY: help

.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

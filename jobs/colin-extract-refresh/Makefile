.PHONY: help setup install build build-nc run

MKFILE_PATH:=$(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_ABS_DIR:=$(patsubst %/,%,$(dir $(MKFILE_PATH)))

DOCKER_NAME:=colin-extract-refresh
TAG_NAME ?= dev
DOCKER_PLATFORM ?= --platform linux/amd64

#################################################################################
# COMMANDS -- Setup                                                             #
#################################################################################
setup: install  ## Setup the project

install:  ## Install python virtual environment
	test -f .venv/bin/activate || python3.11 -m venv  $(CURRENT_ABS_DIR)/.venv ;\
	. .venv/bin/activate ;\
	pip install --upgrade pip ;\
	pip install -Ur requirements.txt

run: ## Run the project in local
	. .venv/bin/activate && python test_connectivity.py

build:
	docker build ${DOCKER_PLATFORM} -t $(DOCKER_NAME):$(TAG_NAME) $(CURRENT_ABS_DIR) \
		--build-arg VCS_REF=$$(git -C $(CURRENT_ABS_DIR) rev-parse --short HEAD 2>/dev/null || echo missing) \
		--build-arg BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ")

build-nc:
	docker build ${DOCKER_PLATFORM} --no-cache -t $(DOCKER_NAME):$(TAG_NAME) $(CURRENT_ABS_DIR)

run-docker: build
	docker run --rm --env-file $(CURRENT_ABS_DIR)/.env $(DOCKER_NAME):$(TAG_NAME)

#################################################################################
# Self Documenting Commands                                                     #
#################################################################################
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

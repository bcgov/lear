DOCKER_NAME:=business-digital-credentials

#################################################################################
# COMMANDS -- Setup                                                             #
#################################################################################

#################################################################################
# COMMANDS - CI                                                                 #
#################################################################################
.PHONY: build

build: ## Build the docker container
	docker build . -t $(DOCKER_NAME) \
	    --platform linux/amd64 \
	    --build-arg VCS_REF=$(shell git rev-parse --short HEAD) \
	    --build-arg BUILD_DATE=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

build-nc: ## Build the docker container without caching
	docker build -

#################################################################################
# COMMANDS - Local                                                              #
#################################################################################
run-dev: ## Run in development mode with hot reload
	docker rm -f business-digital-credentials-queue || true
# 	docker run \
# 		--rm \
# 		--name business-digital-credentials-queue \
# 		--env-file .env \
# 		-e FLASK_ENV=development \
#         -e PYTHONPATH=/code/vendor/business-registry-digital-credentials/src:/code/vendor/business-registry-model/src \
# 		-p 8080:8080 \
# 		-v $(PWD)/src:/code/src \
# 		-v $(realpath ../../../../lear/python/common/business-registry-digital-credentials):/code/vendor/business-registry-digital-credentials \
# 		-v $(realpath ../../../../lear/python/common/business-registry-model):/code/vendor/business-registry-model \
# 		business-digital-credentials
	docker run \
		--rm \
		--name business-digital-credentials-queue \
		--env-file .env \
		-e FLASK_ENV=development \
		-p 8080:8080 \
		-v $(PWD)/src:/code/src \
		business-digital-credentials

run: ## Run the project in local
	docker rm -f business-digital-credentials-queue || true
	docker run \
        --rm \
        --name business-digital-credentials-queue \
        --env-file .env \
        -p 8080:8080 \
        business-digital-credentials

test: ## Unit testing
	poetry run pytest --cov=src --cov-report=xml --cov-report=html --cov-report=term --cov-report=term-missing

coverage-check:
	poetry run pytest --cov=src --cov-fail-under=85

#################################################################################
# Self Documenting Commands                                                     #
#################################################################################
.PHONY: help

.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

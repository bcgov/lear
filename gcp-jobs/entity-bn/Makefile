DOCKER_NAME:=business-entity-bn

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
	docker build --no-cache -t $(DOCKER_NAME) .

#################################################################################
# COMMANDS - Local                                                              #
#################################################################################

#################################################################################
# Self Documenting Commands                                                     #
#################################################################################
.PHONY: help

.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

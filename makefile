#!make

.PHONY: show-help
.PHONY: local-project setup-local-env build-local-project run-local-project stop-local-project

# -----------------------------------------------------------------------------
# -=- Local Project Tasks
# -----------------------------------------------------------------------------

## Task Alias: Builds the whole project locally
local-project: setup-local-env build-local-project run-local-project

## Sets the configuration to a local-build
setup-local-env:
	@cp ./coops-ui/public/config/local-configuration.json ./coops-ui/public/config/configuration.json
	@cp -R ./legal-api/src/legal_api/models ./legal-test-fixture/legal_api
	@cp -R ./legal-api/src/legal_api/exceptions ./legal-test-fixture/legal_api
	@cp ./legal-api/src/legal_api/schemas.py ./legal-test-fixture/legal_api

## Builds the local project
build-local-project:
	@docker-compose -f ./docker-compose.yml build

## Runs the locally built project
run-local-project:
	@docker-compose -f ./docker-compose.yml up -d

## Stops the locally running project
stop-local-project:
	@docker-compose -f ./docker-compose.yml down

## Shell into local container
local-workspace:
	@echo "Shelling into local application..."
	@docker exec -it bcros_frontend bash

## Shell into local development logs
logs:
	@echo "Watching logging output for local development container..."
	@docker logs -f $(shell docker inspect --format="{{.Id}}" bcros_frontend)


#################################################################################
# Self Documenting Commands                                                     #
#################################################################################

.DEFAULT_GOAL := show-help

# Inspired by <http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html>
# sed script explained:
# /^##/:
# 	* save line in hold space
# 	* purge line
# 	* Loop:
# 		* append newline + line to hold space
# 		* go to next line
# 		* if line starts with doc comment, strip comment character off and loop
# 	* remove target prerequisites
# 	* append hold space (+ newline) to line
# 	* replace newline plus comments by `---`
# 	* print line
# Separate expressions are necessary because labels cannot be delimited by
# semicolon; see <http://stackoverflow.com/a/11799865/1968>
.PHONY: show-help
show-help:
	@echo "$$(tput bold)Available rules:$$(tput sgr0)"
	@echo
	@sed -n -e "/^## / { \
		h; \
		s/.*//; \
		:doc" \
		-e "H; \
		n; \
		s/^## //; \
		t doc" \
		-e "s/:.*//; \
		G; \
		s/\\n## /---/; \
		s/\\n/ /g; \
		p; \
	}" ${MAKEFILE_LIST} \
	| LC_ALL='C' sort --ignore-case \
	| awk -F '---' \
		-v ncol=$$(tput cols) \
		-v indent=19 \
		-v col_on="$$(tput setaf 6)" \
		-v col_off="$$(tput sgr0)" \
	'{ \
		printf "%s%*s%s ", col_on, -indent, $$1, col_off; \
		n = split($$2, words, " "); \
		line_length = ncol - indent; \
		for (i = 1; i <= n; i++) { \
			line_length -= length(words[i]) + 1; \
			if (line_length <= 0) { \
				line_length = ncol - indent - length(words[i]) - 1; \
				printf "\n%*s ", -indent, " "; \
			} \
			printf "%s ", words[i]; \
		} \
		printf "\n"; \
	}' \
	| more $(shell test $(shell uname) = Darwin && echo '--no-init --raw-control-chars')

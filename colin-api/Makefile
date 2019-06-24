.PHONY: license
.PHONY: setup clean clean-build clean-pyc clean-test

.PHONY: docker-setup network build start qa style safety test test-travis flake8 \
isort isort-save stop docker-clean logs
.PHONY: mac-cov pylint flake8

SHELL:=/bin/bash
mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))
current_abs_dir := $(patsubst %/,%,$(dir $(mkfile_path)))

#################################################################################
# COMMANDS                                                                      #
#################################################################################
clean: clean-build clean-pyc clean-test
	rm -rf venv/

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	find . -name '.pytest_cache' -exec rm -fr {} +
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

setup: clean venv/bin/activate install-dev

venv/bin/activate: requirements/prod.txt requirements/dev.txt
	rm -rf venv/
	test -f venv/bin/activate || python3 -m venv  $(current_abs_dir)/venv
	. venv/bin/activate ;\
	pip install --upgrade pip ;\
	pip install -Ur requirements/prod.txt ;\
	pip freeze | sort > requirements.txt ;\
	pip install -Ur requirements/dev.txt
	touch venv/bin/activate  # update so it's as new as requirements/prod.txt

.PHONY: install-dev
install-dev: venv/bin/activate
	. venv/bin/activate ; \
	pip install -e .

.PHONY: activate
activate: venv/bin/activate
	. venv/bin/activate

.PHONY: local-test
local-test: venv/bin/activate
	. venv/bin/activate ; \
	pytest

.PHONY: local-coverage
local-coverage: venv/bin/activate
	. venv/bin/activate ; \
	coverage run -m pytest

.PHONY: coverage-report
coverage-report: local-coverage
	. venv/bin/activate ; \
	coverage report ; \
	coverage html

## Run the coverage report and display in a browser window
mac-cov:	install-dev coverage-report
	open -a "Google Chrome" htmlcov/index.html

## run pylint on the package and tests
pylint:
	pylint --rcfile=setup.cfg \
	 --load-plugins=pylint_flask \
	 --disable=C0301,W0511 \
	 colin_api

## run flake8 on the package and tests
flake8:
	flake8 colin_api tests

## Verify source code license headers.
license:
	./scripts/verify_license_headers.sh colin_api tests

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

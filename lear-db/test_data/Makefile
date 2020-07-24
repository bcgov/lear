.PHONY: setup build-req clean clean-build clean-pyc clean-test

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

build-req: clean venv/bin/activate

setup: clean setup-venv install-dev

venv/bin/activate: requirements/prod.txt requirements/dev.txt
	rm -rf venv/
	test -f venv/bin/activate || python3 -m venv  $(current_abs_dir)/venv
	. venv/bin/activate ;\
	pip install --upgrade pip ;\
	pip install -Ur requirements/prod.txt ;\
	pip freeze | sort > requirements.txt ;\
	cat requirements/bcregistry-libraries.txt >> requirements.txt ;\
	pip install -Ur requirements/bcregistry-libraries.txt ;\
	pip install -Ur requirements/dev.txt
	touch venv/bin/activate  # update so it's as new as requirements/prod.txt

setup-venv: requirements.txt
	rm -rf venv/
	test -f venv/bin/activate || python3 -m venv  $(current_abs_dir)/venv
	. venv/bin/activate ;\
	pip install --upgrade pip ;\
	pip install -Ur requirements.txt

.PHONY: install-dev
install-dev: venv/bin/activate
	. venv/bin/activate ; \
	pip install -Ur requirements/dev.txt; \

.PHONY: activate
activate: venv/bin/activate
	. venv/bin/activate

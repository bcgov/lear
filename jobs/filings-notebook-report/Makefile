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
	find . -name '*.egg' -exec rm -fr {} +

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


setup: clean create-venv install-dev

create-venv: 	
	test -f venv/bin/activate || python3 -m venv  $(current_abs_dir)/venv
	
install-dev:
	. venv/bin/activate ; \
	pip install --upgrade pip ;\
	pip install -Ur requirements/prod.txt ;\
	pip install -Ur requirements/dev.txt
	
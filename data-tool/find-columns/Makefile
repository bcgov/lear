# Python virtual environment
VENV = venv
PYTHON = python3
VENV_ACTIVATE = $(VENV)/bin/activate

.PHONY: setup run clean

setup: $(VENV)
	. $(VENV_ACTIVATE) && pip install --upgrade pip && pip install -r requirements.txt

$(VENV):
	$(PYTHON) -m venv $(VENV)

run:
	. $(VENV_ACTIVATE) && $(PYTHON) find_null_columns.py

clean:
	rm -rf $(VENV)
	rm -rf __pycache__

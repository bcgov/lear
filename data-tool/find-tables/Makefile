# Setup dependencies
setup: clean
	test -f venv/bin/activate || python3 -m venv  venv ;\
	. venv/bin/activate ;\
	pip install -Ur requirements.txt

# Clean up project
clean:
	rm -rf venv +
	find . -name '__pycache__' -exec rm -fr {} +

# Run helper
run:
	. venv/bin/activate && python find_tables.py
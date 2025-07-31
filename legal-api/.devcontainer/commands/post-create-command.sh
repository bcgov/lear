echo "Running post-create-command.sh"

export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

poetry config virtualenvs.in-project true --local
poetry install --all-extras
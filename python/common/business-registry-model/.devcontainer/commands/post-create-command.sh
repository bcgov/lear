echo "Running post-create-command.sh"

poetry config virtualenvs.in-project true --local
poetry install --all-extras
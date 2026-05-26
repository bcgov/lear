echo "Running post-create-command.sh"

python -m venv .venv
./.venv/bin/activate

pip install --no-cache-dir -r requirements.txt
pip install .

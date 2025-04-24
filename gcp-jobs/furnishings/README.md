# Business Registry Furnishings job

## Tech Design
https://community.inkdrop.app/a27b7a79c8cdf7db0ab19be10b4fc2e8/lr3hwYXNS#emailer

## Setup
Clone the repo and submit a PR from a new branch.

### Install the dependencies
```bash
poetry install
```

### Configure the .env
(see .env.sample)

```bash
eval $(poetry env activate)
```

### Run the job
```bash
python furnish.py
```

### Run Linting
```bash
ruff check --fix
```

### Run unit tests
```bash
pytest
```
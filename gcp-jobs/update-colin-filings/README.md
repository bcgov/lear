# Business Registry Update COLIN Filings job

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
python run_job.py
```

### Run Linting
```bash
ruff check --fix
```

### Run unit tests
```bash
pytest
```
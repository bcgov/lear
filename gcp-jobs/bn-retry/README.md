# BN Retry

BN15 retry GCP job for firms created in LEAR.

## Overview

This job checks BN15 status for businesses firms:
- Queries businesses with identifiers not starting with 'FM0' that don't have a valid BN15 (FM0's are old, created in colin)
- Checks BN15 status via Colin API `/program_account/<identifier>` endpoint
- Updates LEAR database with BN15 when received
- Sends email notification via BUSINESS_EMAILER_TOPIC
- Publishes business change event to BUSINESS_EVENTS_TOPIC

## Poetry

You may prefer to have the vitrual-environment in the project home. To do that, tell poetry to use a local .venv before
installing.

```shell
poetry config virtualenvs.in-project true
```

```shell
poetry install
```

You can issue any command in the current environment, via poetry's shell

```shell
source $(poetry env activate)
```

### Run the job

```bash
python run.py
```

### Run Linting

```bash
ruff check
```

### Run unit tests

```
pytest
```

## Deployment

The job is deployed to GCP Cloud Run and scheduled to run daily at 6AM via Cloud Scheduler.

See `devops/gcp-cloudbuild.yaml` for build configuration and `schedules/bn-retry-schedule.yaml` for scheduler configuration.

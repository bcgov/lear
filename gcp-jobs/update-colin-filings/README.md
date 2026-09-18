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

## Configuration notes

### SKIPPED_IDENTIFIERS

Comma-separated list of business identifiers (e.g. `BC0879787,CP0001463`) whose filings are known
data-drift cases and should not be sent to COLIN. Filings for these businesses are skipped and
counted separately in the end-of-run summary (`Skipped (known drift)`).

Typical drift cases:
- the business does not exist in COLIN (`<corp_num> not found` errors)
- the business already exists in COLIN, so re-sending its incorporation/amalgamation fails with
  `ORA-00001: unique constraint (PK_CORPORATION) violated`

Note: an ORA-00001 can also mean the filing WAS created in COLIN but the job failed to write the
`colinIds` back to LEAR (see the `MANUAL ACTION REQUIRED` log message). Adding such a business to
this list hides the error but does not repair it — the `colin_event_ids` row still needs to be
inserted in LEAR manually.
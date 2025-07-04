# Document Record Service Integration

This module provides a service class and a set of document-related constants used to interact with the **Document Record Service (DRS)**. It supports uploading, updating, deleting, retrieving, and validating PDF documents.

---

## Required env values to use
```code
DOC_API_KEY=""
DOC_API_ACCOUNT_ID=""
DOC_API_URL=""
```

## Poetry
You may prefer to have the vitrual-environment in the project home. To do that, tell poetry to use a local .venv before installing.
```shell
poetry config virtualenvs.in-project true
```
```shell
poetry install
```

You can issue any command in the current environment, via poetry's shell
```shell
poetry shell
```

### Aside: faster local dev?
change the git installed services to the local versions and rebuild the lockfile
```bash
poetry lock
```
remember to switch them back before the final PR


## Tests
pytest
---

## 🛠️ TODO

- Add unit tests for each DRS method.
- Improve error handling with more granular exceptions.
- Document the `RequestInfo` data structure in detail.

---
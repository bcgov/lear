# Business Registry Model


# Contributing

## Linting
For now the lint checks must be doing manually. Please run ruff and fix all issues until you get a clean run, signigifed by a `All checks passed!`
```bash
ruff --config pyproject.toml check --fix
```

## Testing
The test suite uses *testcontainers*, you can run it locally or you can use the _.devcontainer_ service available is a number of IDEs.

This library uses `pytest`. All test should pass.
Running this should give you a fully passing and cleared run.
```bash
pytest tests
```
### Determining data collisions
If you are working on tests and have some data collisions, there's a couple of approaches. You can run the tests using the following command continually to ensure the test logic works.
```bash
pytest --lf tests
```
Once you know all the tests pass individually, you can determine what fields are colliding and set appropriately.



## Note about migrations setting the directory
```python
import business_model_migrations
...
Migrate(
            app,
            _db,
            directory=business_model_migrations.__path__[0],

```
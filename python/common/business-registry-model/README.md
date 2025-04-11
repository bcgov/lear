# Business Registry Model

## Note about migrations setting the directory
```python
import business_model_migrations
...
Migrate(
            app,
            _db,
            directory=business_model_migrations.__path__[0],

```
from registry_schemas.flask import SchemaServices

rsbc_schemas = SchemaServices()  # pylint: disable=invalid-name


__all__ = (
    "rsbc_schemas",
    "build_schema_error_response",
)


def build_schema_error_response(errors):
    """Provide a formatted error response for schema errors."""
    formatted_errors = []
    for error in errors:
        validation_errors = []
        for context in error.context:
            validation_errors.append(
                {
                    "message": context.message,
                    "jsonPath": context.json_path,
                    "validator": context.validator,
                    "validatorValue": context.validator_value,
                }
            )
        formatted_errors.append(
            {
                "path": "/".join(error.path),
                "error": error.message,
                "context": validation_errors,
            }
        )
    return formatted_errors

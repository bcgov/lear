"""Application Specific Exceptions, to manage the business errors.

@log_error - a decorator to automatically log the exception to the logger provided

BusinessException - error, status_code - Business rules error
error - a description of the error {code / description: classname / full text}
status_code - where possible use HTTP Error Codes
"""
import functools


class BusinessException(Exception):
    """Exception that adds error code and error name, that can be used for i18n support."""

    def __init__(self, error, status_code, *args, **kwargs):
        """Return a valid BusinessException."""
        super(BusinessException, self).__init__(*args, **kwargs)
        self.error = error
        self.status_code = status_code

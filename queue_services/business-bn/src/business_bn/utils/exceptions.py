
# BNExceptionn
# BNRetryExceededException
# QueueException

"""Exceptions defined for the business_bn service."""

class QueueException(Exception):
    """Base exception for the Queue Services."""


class BNException(Exception):
    """BN exception for the Queue Services."""


class BNRetryExceededException(Exception):
    """BN retry exceeded exception for the Queue Services."""

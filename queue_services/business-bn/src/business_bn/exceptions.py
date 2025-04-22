# BNExceptionn
# BNRetryExceededException
# QueueException

"""Exceptions defined for the business_bn service."""


class QueueException(Exception): # noqa: N818
    """Base exception for the Queue Services."""


class BNException(Exception): # noqa: N818
    """BN exception for the Queue Services."""


class BNRetryExceededException(Exception): # noqa: N818
    """BN retry exceeded exception for the Queue Services."""

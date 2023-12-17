"""
cmit.requests.exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module contains the exceptions in the cmit.requests package.
"""


class CMITException(IOError):
    """
    Ambiguous CMIT exception.
    """

    def __init__(self, *args, **kwargs):
        response = kwargs.pop('response', None)
        self.response = response
        self.request = kwargs.pop('request', None)
        if response is not None and not self.request and hasattr(response, 'request'):
            self.request = self.response.request
        super().__init__(*args, **kwargs)


class CMITError(CMITException):
    """
    A CMIT error occurred.
    """
    pass


class CMITConnectionError(CMITException):
    """
    A CMIT connection error occurred.
    """
    pass


class CMITTimeout(CMITException):
    """
    The CMIT request timed out.
    """
    pass


class MissingSchema(CMITException, ValueError):
    """
    The path schema (e.g. cmit or unix) is missing.
    """
    pass


class InvalidSchema(CMITException, ValueError):
    """
    The path schema is invalid.
    """
    pass


class InvalidSocketPath(CMITException, ValueError):
    """
    The socket path is invalid.
    """
    pass
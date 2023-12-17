"""
A Library for interacting with a CMIT server.

Basic PING usage:

    >>> from cmit import requests
    >>> req = requests.ping('cmit://tmp/cmit.sock', 'test', 'test')
    >>> req.status_code
    200
"""

from .api import request, ping, execute, poll
from .exceptions import (
    CMITException, CMITError, CMITConnectionError, CMITTimeout, MissingSchema, InvalidSchema, InvalidSocketPath
)
from .models import PreparedRequest, Request, Response
from .sessions import Session


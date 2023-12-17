"""
A python implementation of the Common Messaging Interface Transport (CMIT) protocol.

As a protocol CMIT is designed to support internal process communication (IPC) within
a single node. Consequently, this current version only supports serving through a
UNIX domain socket. By default, CMIT supports 3 message command verbs (PING, EXECUTE, POLL).
However, CMIT is designed to be very flexible, and you may augment it with your own command verbs.

Note:
    The default handler (:class:`SimpleCMITRequestHandler`) will accept POLL and EXECUTE requests, the actual processing
    of these requests is left up to the final implementation. That is, they are simply acknowledged.
"""

from enum import IntEnum

__version__ = "0.1.0"


class CMITStatus(IntEnum):

    def __new__(cls, value, phrase, description=''):
        obj = int.__new__(cls, value)
        obj._value_ = value

        obj.phrase = phrase
        obj.description = description
        return obj

    # 1xx Informational
    CONTINUE = 100, 'Continue', 'Request received, please continue'
    PROCESSING = 102, 'Processing', 'Request in progress'

    # 2xx Success
    OK = 200, 'OK', 'Request fulfilled, document follows'
    ACCEPTED = 202, 'Accepted', 'Request accepted, processing continues off-line'

    # 3xx Client Error
    BAD_REQUEST = 300, 'Bad Request', 'Bad request syntax or unsupported method'
    UNAUTHORIZED = 301, 'Unauthorized', 'No permission -- see authorization schemes'

    # 4xx Server Error
    INTERNAL_SERVER_ERROR = 400, 'Internal Server Error', 'Server got itself in trouble'
    NOT_IMPLEMENTED = 401, 'Not Implemented', 'Server does not support this operation'
    BAD_GATEWAY = 402, 'Bad Gateway', 'Invalid responses from another server/proxy'
    SERVICE_UNAVAILABLE = 403, 'Service Unavailable', 'The server cannot process the request due to a high load'

    @property
    def is_informational(self):
        return 100 <= self.value <= 199

    @property
    def is_success(self):
        return 200 <= self.value <= 299

    @property
    def is_client_error(self):
        return 300 <= self.value <= 399

    @property
    def is_server_error(self):
        return 400 <= self.value <= 499


# class CMITMethod(StrEnum):
#
#     def __new__(cls, value, description=''):
#         obj = str.__new__(cls, value)
#         obj._value_ = value
#
#         obj.description = description
#         return obj
#
#     def __repr__(self):
#         return "<%s.%s>" % (self.__class__.__name__, self.name)
#
#     PING = 'PING', 'Ping the server to check if its alive'
#     POLL = 'POLL', 'Poll for resource status'
#     EXECUTE = 'EXECUTE', 'Execute a message request'


__all__ = ['CMITStatus']

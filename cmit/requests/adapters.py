"""
cmit.requests.adapters
~~~~~~~~~~~~~~~~~~~~~~~~~

This module contains the transport adapters tha cmit.requests uses to
define and maintain connections.
"""

import typing
from secrets import randbits

from cmit.client import CMITConnection, error

from .models import PreparedRequest, Request, Response
from ._internal_utils import parse_socket_path


class BaseAdapter:
    """The Base Transport Adapter"""

    def __init__(self):
        super().__init__()

    def send(self, request, timeout=None, **kwargs) -> Response:
        """
        Sends the request to the server

        :param request: :class:`PreparedRequest<PreparedRequest>` to send.
        :type request: cmit.requests.models.PreparedRequest
        :param timeout: (optional) How long to wait for the server to send data
        :type timeout: float or tuple
        """
        raise NotImplementedError

    def close(self):
        """Closes the connection to the server"""
        raise NotImplementedError


class CMITAdapter(BaseAdapter):

    __attrs__ = [
        "connection",
        "config",
    ]

    connection: typing.Optional[CMITConnection] = None

    def __getstate__(self):
        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        self.config = {}

        for attr, value in state.items():
            setattr(self, attr, value)

    def build_response(self, request, response):
        """
        Builds a :class:`Response <Response>` object from a CMIT response.

        :param request: :class:`PreparedRequest<PreparedRequest>` that was used to generate the response.
        :type request: cmit.requests.models.PreparedRequest
        :param response: :class:`CMITResponse<CMITResponse>` object.
        :type response: cmit.client.CMITResponse
        """

        resp = Response()
        response.begin()
        resp.socket_path = response.sock_path
        resp.status_code = response.status
        resp.reason = response.reason
        resp.topic = response.msg.topic
        resp.msg_id = response.msg.msg_id
        resp.request = request
        resp.msg = response.msg
        resp.connection = self
        response.close()

        return resp

    def get_connection(self, fp):
        """
        Returns a :class:`CMITConnection <CMITConnection>` object for the given socket path.

        :param fp: A file-like object to send the request to.
        :return: :class:`CMITConnection<CMITConnection>`
        :rtype: cmit.client.CMITConnection
        """

        parsed = parse_socket_path(fp)
        socket_path = parsed.socket_path

        if self.connection is not None and self.connection.socket != socket_path:
            connection = self.connection
            self.connection = None
            connection.close()
            connection = CMITConnection(socket_path)

        elif self.connection is not None and self.connection.socket == socket_path:
            connection = self.connection

        else:
            connection = CMITConnection(socket_path)
            self.connection = connection

        return connection

    def send(self, request, timeout=None, **kwargs) -> Response:
        """
        Sends the request to the server

        :param request: :class:`PreparedRequest<PreparedRequest>` to send.
        :type request: cmit.requests.models.PreparedRequest
        :param timeout: (optional) How long to wait for the server to send data
        :type timeout: float or tuple
        """
        msg_id = kwargs.get("msg_id", "%032x" % randbits(128))
        try:
            connection = self.get_connection(request.socket_path)
            connection.connect()
            msg_id = connection.request(request.command, request.topic, request.payload, msg_id=msg_id)
            request.msg_id = msg_id
            response = connection.getresponse()
        except error as e:
            raise e
        except Exception as e:
            raise e

        return self.build_response(request, response)

    def close(self):
        """Closes the connection to the server"""
        if self.connection is not None:
            self.connection.close()
            self.connection = None

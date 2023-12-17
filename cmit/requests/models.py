"""
cmit.requests.models
~~~~~~~~~~~~~~~~~~~~~~~

This module contains the models that power the cmit.requests package.
"""
import json
import os
import datetime
from urllib.parse import urlunparse
from requests.utils import requote_uri

from cmit.requests._internal_utils import to_native_str, parse_socket_path
from cmit.requests.exceptions import InvalidSocketPath, MissingSchema

_NULL_TOPIC = "topic.null"


class Request:

    def __init__(self, command=None, socket_path=None, topic=None, data=None, rpc_args=None, rpc_kwargs=None):

        # create default values for the request
        topic = _NULL_TOPIC if topic is None else topic
        data = [] if data is None else data
        rpc_args = [] if rpc_args is None else rpc_args
        rpc_kwargs = {} if rpc_kwargs is None else rpc_kwargs

        self.command = command
        self.socket_path = socket_path
        self.topic = topic
        self.data = data
        self.rpc_args = rpc_args
        self.rpc_kwargs = rpc_kwargs

    def __repr__(self):
        return f"<Request [{self.command}]>"

    def prepare(self):
        """
        Constructs a :class:`PreparedRequest <PreparedRequest>` for transmission and returns it.
        :return: :class:`PreparedRequest<PreparedRequest>`
        :rtype: cmit.requests.models.PreparedRequest
        """
        p = PreparedRequest()
        p.prepare(self.command, self.socket_path, self.topic, self.data, self.rpc_args, self.rpc_kwargs)
        return p


class PreparedRequest:

    def __init__(self):

        # CMIT Command to send to the server
        self.command = None

        # Unix Domain Socket to send the request to
        self.socket_path = None

        # Topic to route the request to
        self.topic = None

        # Request message data
        self.payload = None

        # Request message id
        self.msg_id = None

    def __repr__(self):
        return f"<PreparedRequest [{self.command}]>"

    def prepare(self, command, socket_path, topic, data=None, msg_args=None, msg_kwargs=None):

        self.prepare_command(command)
        self.prepare_socket_path(socket_path)
        self.prepare_topic(topic)
        self.prepare_payload(data, msg_args, msg_kwargs)

    def copy(self):
        p = PreparedRequest()
        p.command = self.command
        p.socket_path = self.socket_path
        p.payload = self.payload

        return p

    def prepare_command(self, command):
        self.command = command
        if self.command is not None:
            self.command = to_native_str(self.command)

    def prepare_socket_path(self, socket_path):

        if isinstance(socket_path, bytes):
            socket_path = socket_path.decode("utf-8")
        else:
            socket_path = str(socket_path)

        socket_path = socket_path.strip()

        if socket_path == "":
            raise ValueError("socket_path cannot be empty")

        if ":" in socket_path and not socket_path.lower().startswith("cmit"):
            raise ValueError("socket_path must be a unix domain socket")

        try:
            scheme, path, file_type = parse_socket_path(socket_path)
        except Exception as e:
            raise InvalidSocketPath(f"File Path for Socket doesn't exist {socket_path!r}") from e

        if not scheme:
            raise MissingSchema(
                f"Invalid Socket Path {socket_path!r}: No schema supplied. "
                f"Perhaps you meant cmit://{socket_path!r}?"
            )

        if not path:
            raise InvalidSocketPath(f"Invalid Socket Path {socket_path!r}: No path supplied.")

        try:
            os.stat(path+file_type)
        except FileNotFoundError as e:
            raise InvalidSocketPath(f"File Path for Socket doesn't exist {socket_path!r}") from e

        socket_path = requote_uri(urlunparse((scheme, path+file_type, "", "", "", "")))
        self.socket_path = socket_path

    def prepare_topic(self, topic):

        if callable(topic):
            topic = topic()

        self.topic = topic

        if self.topic is not None and not callable(self.topic):
            self.topic = to_native_str(self.topic)

    def prepare_payload(self, msg_data, msg_args, msg_kwargs=None):
        """
        Prepares the payload for transmission.
        """

        payload = {
            "args": [i for i in msg_args],
            "kwargs": {},
            "data": msg_data
        }

        if msg_kwargs:
            payload["kwargs"] = {k: v for k, v in msg_kwargs.items()}

        self.payload = json.dumps(payload)


class Response:
    """
    The :class:`Response<Response>` object, which contains a
    server's response to a CMIT request.
    """

    __attrs__ = [
        "request",
        "status_code",
        "socket_path",
        "topic",
        "reason",
        "msg_id",
        "elapsed",
        "msg"
    ]

    def __init__(self):

        # Integer representation of the response status code.
        self.status_code = None

        # Reason of the response.
        self.reason = None

        # Socket Path of the response.
        self.socket_path = None

        # Topic of the response.
        self.topic = None

        # Message ID of the response.
        self.msg_id = None

        #: The amount of time elapsed between sending the request
        #: and the arrival of the response (as a timedelta).
        self.elapsed = datetime.timedelta(0)

        # The prepared request that was sent to create the response.
        self.request = None

        # The CMITMessage object
        self.msg = None

    def __repr__(self):
        return f"<Response [{self.status_code}]>"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __getstate__(self):
        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        for name, value in state.items():
            setattr(self, name, value)

    def close(self):
        """
        Releases the connection back to the CMITConnection pool. Once this
        method has been called the underlying raw socket must not be accessed
        again.
        """
        pass

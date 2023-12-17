import errno
import io
import os
import re
import json
import socket
import typing
from secrets import randbits
from typing import Union

from .messages import CMITMessage
from .typing import PayloadType, TopicType
from .utils import create_connection, encode as _encode


DEFAULT_CMITP_SOCKET = "/tmp/cmitp.sock"

_UNKNOWN = "UNKNOWN"

_CS_IDLE = "Idle"
_CS_REQ_STARTED = "Request-Started"
_CS_REQ_SENT = "Request-Sent"

_MAXLINE = 65536

_contains_disallowed_url_pchar_re = re.compile("[\x00-\x20\x7f]")


def parse_message(fp: io.BufferedIOBase):
    """
    Parse a CMITP message from a file pointer.

    :param fp: The file pointer to read from.
    :return: A dict containing the parsed message.
    """

    # first line should be blank
    line = fp.readline(_MAXLINE + 1)
    if len(line) > _MAXLINE:
        raise LineTooLong("seperation line")

    if line != b"\r\n":
        raise ValueError("Invalid seperation line")

    # second line should be the message
    line = fp.readline(_MAXLINE + 1)
    if len(line) > _MAXLINE:
        raise LineTooLong("message line")

    if not line:
        raise RemoteDisconnected("Remote end closed connection without response")

    try:
        msg = CMITMessage.parse_message(line)
    except ValueError as ve:
        raise ValueError("Invalid message") from ve

    return msg


class CMITResponse(io.BufferedIOBase):

    # CMITPResponse is a file-like object that reads from a CMITP socket
    # CMITPResponse is formatted as follows:
    #   {CMITP Version} {Status Code} {Reason Message}\r\n
    #   {blank line}
    #   {CMITP Message}

    def __init__(self, sock: socket.socket, **kwargs):
        self.fp = sock.makefile("rb")
        self.sock_path = sock.getsockname()
        self.will_close = True

        self.version = _UNKNOWN
        self.status = _UNKNOWN
        self.reason = _UNKNOWN

        self.msg: typing.Optional[CMITMessage] = None

    def _read_status(self):
        line = str(self.fp.readline(_MAXLINE + 1), "utf-8")
        if len(line) > _MAXLINE:
            raise LineTooLong("status line")

        if not line:
            raise RemoteDisconnected("Remote end closed connection without response")

        try:
            version, status, reason = line.split(None, 2)
        except ValueError:
            try:
                version, status = line.split(None, 1)
                reason = ""
            except ValueError:
                # empty version will cause next test to fail.
                version = ""

        if not version.startswith("CMIT/"):
            self._close_conn()
            raise BadStatusLine(line)

        try:
            status = int(status)
            if not 100 <= status <= 999:
                raise BadStatusLine(line)
        except ValueError:
            raise BadStatusLine(line)

        return version, status, reason

    def begin(self):

        if self.msg is not None:
            return

        while True:
            version, status, reason = self._read_status()

            if status != 100:
                break

        self.status = status
        self.reason = reason.strip()
        if version in ("CMIT/1.0", ):
            self.version = 10
        else:
            raise UnknownProtocol(version)

        self.msg = parse_message(self.fp)

    def _close_conn(self):
        fp = self.fp
        self.fp = None
        if fp:
            fp.close()

    def close(self):
        try:
            super().close()
        finally:
            if self.fp:
                self._close_conn()

    def flush(self):
        super().flush()
        if self.fp:
            self.fp.flush()

    def isclosed(self):
        """True if the connection is closed."""
        return self.fp is None


class CMITConnection:

    _cmitp_vsn = 10
    _cmitp_vsn_str = 'CMIT/1.0'

    response_class = CMITResponse
    default_socket = DEFAULT_CMITP_SOCKET
    auto_open = 1

    def __init__(self, socket_fp=None, block_size=8192):

        self.sock = None
        self.block_size = block_size
        self._buffer = []
        self.__response = None
        self.__state = _CS_IDLE
        self.__messages = {}
        self.socket = socket_fp if socket_fp is not None else self.default_socket

        self._validate_socket_path(self.socket)

    def connect(self):
        self.sock = self._create_connection()

        try:
            self.sock.settimeout(120.0)
        except OSError as e:
            if e.errno in (errno.ENOPROTOOPT, errno.EPROTONOSUPPORT):
                raise

    def _create_connection(self):
        sock = None
        err = None
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, socket.IPPROTO_IP)
            sock.connect(self.socket)
            return sock
        except OSError as _:
            err = _
            if sock is not None:
                sock.close()

        if err is not None:
            try:
                raise err
            finally:
                err = None
        else:
            raise OSError("Can't connect to %r" % self.socket)

    def close(self):
        """
        Close the connection to the CMITP server.
        """

        self.__state = _CS_IDLE

        try:
            sock = self.sock
            if sock:
                self.sock = None
                sock.close()
        finally:
            response = self.__response
            if response:
                self.__response = None
                response.close()

    def end_request(self):
        """
        This method sends the end of request message to the server.
        """

        # Change state to indicate that the request has been sent.
        if self.__state == _CS_REQ_STARTED:
            self.__state = _CS_REQ_SENT
        else:
            raise ImproperConnectionState("Request not started")

        self.send("\r\n")

    def request(self, command: str, topic: TopicType, payload: PayloadType = "", msg_id=None):
        """
        Send a CMITP request to the server.

        At this point the topic and payload can be
        strings, bytes, or callable objects.
        """
        if msg_id is None:
            # Generate a new random message id
            msg_id = "%032x" % randbits(128)

        self._send_request(command, topic, payload, msg_id=msg_id)

        return msg_id

    def _send_request(self, command: str, topic: TopicType, payload: PayloadType, msg_id=None):

        if self.__response and self.__response.isclosed():
            self.__response = None

        # Change state to indicate that we are starting a new request.
        if self.__state == _CS_IDLE:
            self.__state = _CS_REQ_STARTED
        else:
            raise CannotSendRequest(self.__state)

        # Create a new message object
        message = CMITMessage(topic, msg_id=msg_id)

        # Set the payload, check if it is a string, dict, or callable
        if isinstance(payload, str) or hasattr(payload, "__call__"):
            message.payload = payload
        elif isinstance(payload, dict):
            message.payload = json.dumps(payload)

        # Cache the message object
        self.__messages[msg_id] = message

        request_line = f"{command.upper()} {self._cmitp_vsn_str}\r\n"
        self.sock.sendall(_encode(request_line, "request line"))
        self.sock.sendall(_encode("\r\n", "blank line"))
        self.sock.sendall(message())

        # Finalize the message
        self.end_request()

    def send(self, data: str):
        """
        Send `data` to the sever.
        ``data`` can be a string object, dict object, or a :class:`CMTIPMessage` object.
        """

        if self.sock is None:
            self.connect()

        data = _encode(data, "data")

        try:
            self.sock.sendall(data)
        except TypeError:
            raise TypeError(
                "data should be a str, dict, iterable, callable, or an instance of CMITPMessage, "
                "got %r" % type(data)
            )

    def getresponse(self):
        """
        Get the response from the server.
        """
        if self.__response and self.__response.isclosed():
            self.__response = None

        if self.__state != _CS_REQ_SENT or self.__response:
            raise ResponseNotReady(self.__state)

        response = self.response_class(self.sock)

        try:
            try:
                response.begin()
            except ConnectionError:
                self.close()
                raise
            assert response.will_close != _UNKNOWN
            self.__state = _CS_IDLE

            if response.will_close:
                self.close()
            else:
                self.__response = response

            return response
        except:
            response.close()
            raise

    @staticmethod
    def _validate_socket_path(socket_fp: Union[os.PathLike, str]):

        match = _contains_disallowed_url_pchar_re.search(socket_fp)

        if match:
            raise InvalidSocketPath(f"File Path for Socket contains illegal characters {socket_fp!r} "
                                    f"(found at least {match.group()!r})")

        try:
            os.stat(socket_fp)
        except FileNotFoundError as fnp:
            raise InvalidSocketPath(f"File Path for Socket doesn't exist {socket_fp!r}") from fnp


class CMITException(Exception):
    pass


class InvalidSocketPath(CMITException):
    pass


class UnknownProtocol(CMITException):
    def __init__(self, version):
        self.args = version,
        self.version = version


class ImproperConnectionState(CMITException):
    pass


class ResponseNotReady(ImproperConnectionState):
    pass


class BadStatusLine(CMITException):
    def __init__(self, line):
        if not line:
            line = repr(line)
        self.args = line,
        self.line = line


class CannotSendRequest(ImproperConnectionState):
    pass


class LineTooLong(CMITException):
    def __init__(self, line_type):
        CMITException.__init__(self, "got more than %d bytes when reading %s" % (_MAXLINE, line_type))


class RemoteDisconnected(ConnectionResetError, BadStatusLine):
    def __init__(self, *pos, **kw):
        BadStatusLine.__init__(self, "")
        ConnectionResetError.__init__(self, *pos, **kw)


error = CMITException

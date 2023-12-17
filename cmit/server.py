"""
CMIT server classes.

Note: BaseCMITRequestHandler doesn't implement any CMIT request; see
SimpleCMITRequestHandler for simple implementation.
"""
import json
import logging
import sys
import socket
import socketserver
import time
from datetime import datetime
from secrets import randbits
from typing import Any

from cmit import CMITStatus
from cmit.abc import _BaseStreamRequestHandler
from cmit.messages import CMITMessage, ServerErrorMessage
from cmit.utils import cmit_response

__version__ = "0.2.0"

_MAXLINE = 65536


class CMITServer(socketserver.TCPServer):
    address_family = socket.AF_UNIX
    logger = logging.getLogger()

    def server_bind(self):
        """Called by constructor to bind the socket.

        May be overridden.

        """
        self.logger.info(f"Binding to CMITServer to {self.server_address}")
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()


class ThreadingCMITServer(socketserver.ThreadingMixIn, CMITServer):
    daemon_threads = True


class BaseCMITRequestHandler(_BaseStreamRequestHandler):

    """
    CMIT Request handler base class.

    The following is an explanation of CMIT to guide you through the code.

    CMIT (Common Messaging Interface Transport) is a protocol built on top
    of a reliable stream transport (e.g. UNIX Socket). The protocol is designed
    primarily to support Inter-Process Communication (IPC) and has two
    parts in a request:

    1. One line identifying the request type
    2. An encrypted JSON message section that contains four fields:
        - _id: a sting to support idempotency
        - timestamp: the POSIX timestamp of the time the request was generated
        - topic: a string used to route the message
        - payload: a string of stringified object being sent to the server for processing

    The first and second part are seperated by a blank line.

    The first line of the request has the form:

    <command> <version>

    Where <command> is a (case-sensitive) keyword such as EXECUTE or POLL,
    and <version> should be the string "CMIT/1.0".

    The specification specifies that lines are separated by CRLF but
    for compatibility with the widest range of clients recommends
    servers also handle LF. Similarly, whitespace in the request line
    is treated sensibly (allowing multiple spaces between components
    and allowing trailing whitespace).

    The reply from the CMIT 1.x protocol also has two parts:

    1. One line with a response code
    2. An encrypted JSON message with the same four fields.

    Also, like a request, the first and second parts are seperated by a blank line.

    The response code has the form:

    <version> <response_code> <response_msg>

    Where <version> is the protocol version ("CMIT/1.0"), <response_code> is
    a 3-digit response code indicating the disposition of the request, and
    <response_msg> is an optional human friendly string explaining what the
    response code means.

    This server parses the request and then calls a function specific to
    the request type (<command>). For example, a request EXECUTE will be
    handled by a method do_EXECUTE(). If no such method exists the server
    sends an error response to the client. If it exists, it is called
    without any arguments:

    do_EXECUTE()

    Note that the request name is case-sensitive.

    The following attributes are available to each instance:

    - command, version are the broken-down request line;

    - rfile is a file object open for reading positioned at the
    start of the message part;

    - wfile is a file object for writing the response.

    IT IS IMPORTANT TO ADHERE TO THE PROTOCOL FOR WRITING!

    The first thing to be written must be the response line. The follow
    with a blank line, and then the response message data.

    """

    # The Python system version, truncated to its first component.
    sys_version = "Python/" + sys.version.split()[0]

    # The server software version. You may override this.
    server_version = "BaseCMIT/" + __version__

    # Message class to use when building an error message
    # must take topic, msg_id, ts, code, and reason as parameters when created.
    error_message_class = ServerErrorMessage

    # The default request version.
    default_protocol_version = "CMIT/1.0"

    # Tracks when it is time to close the request tunnel
    close_connection = False

    responses = {
        v: (v.phrase, v.description)
        for v in CMITStatus.__members__.values()
    }

    logger = logging.getLogger()

    # noinspection PyUnresolvedReferences,PyAttributeOutsideInit
    def parse_request(self):
        """
        Parse a request (internal).

        The request should be stored in the raw_request_line attribute.
        The results stored in the command request_version attributes.

        Return True for success, False for failure; on failure, any relevant
        error response has already been sent back.
        """

        # set default values for command, and request_version
        self.command = None
        self.request_version = version = self.default_protocol_version

        # As of right now all connections close after response
        self.close_connection = True

        # Convert from bytes to str
        request_line = str(self.raw_request_line, 'latin-1')

        # Strip the line ending
        request_line = request_line.rstrip('\r\n')

        # Store the request line
        self.request_line = request_line

        # Split request line into <command> and <version>
        words = request_line.split(None, 2)

        # If request had no request line return false
        if len(words) == 0:
            return False

        # If request has two or more words
        if len(words) >= 2:

            # ...the last is the version
            version = words[-1]

            try:
                # This handler only processes 'CMIT' requests
                if not version.startswith('CMIT/'):
                    raise ValueError

                # split version string, first at the slash...
                base_version_number = version.split('/', 1)[1]

                # ...then at the decimal point.
                version_number = base_version_number.split(".")

                # Protocol specifies that version number is in a major and minor version format
                # ex 1.0 or 1.1
                if len(version_number) != 2:
                    raise ValueError

                # only digits allowed after the '/' in ther version
                if any(not v.isdigit() for v in version_number):
                    raise ValueError("non-digit in CMIT version number")

                # minor version can only be up to 3 digits long
                if any(len(v) > 3 for v in version_number):
                    raise ValueError("version number too long")

                version_number = int(version_number[0]), int(version_number[1])

            except (ValueError, IndexError):
                self.send_error(CMITStatus.BAD_REQUEST, f"Bad protocol version ({version})")
                return False

            if version_number >= (2, 0):
                self.send_error(CMITStatus.BAD_REQUEST, f"Invalid CMIT version ({base_version_number})")
                return False

            # Store request version
            self.request_version = version

            if not 1 <= len(words) <= 2:
                self.send_error(
                    CMITStatus.BAD_REQUEST,
                    "Bad request syntax (%r)" % requestline)
                return False

            # Store request command
            self.command = words[0]

            return True

    def parse_body(self):
        """
        Parse request body (internal)
        """

        self.msg = None

        self.logger.debug(f"parsing spacer")
        spacer = str(self.rfile.readline(_MAXLINE + 1), 'latin-1')

        if spacer != "\r\n":
            self.send_error(CMITStatus.BAD_REQUEST, "Invalid request body")
            return False

        msg_line = str(self.rfile.readline(_MAXLINE + 1), 'latin-1')

        if msg_line == "\r\n":
            self.send_error(CMITStatus.BAD_REQUEST, "Invalid request body")
            return False

        try:
            self.logger.debug(f"msg_line: {msg_line}")

            self.msg = CMITMessage.parse_message(msg_line)

            if not isinstance(self.msg, CMITMessage):
                self.logger.debug(f"Invalid msg type: {type(self.msg)}")

        except json.JSONDecodeError:
            self.logger.error(f"Invalid request body: {msg_line}")
            self.send_error(CMITStatus.BAD_REQUEST, "Malformed request body")
            return False

        return True

    # noinspection PyUnresolvedReferences,PyAttributeOutsideInit
    def handle_one_request(self):
        """
        Handle a single CMIT request.

        This method shouldn't be overridden in most cases.
        See :class:`BaseCMITRequestHandler` :method:`__doc__` string for information
        on how to handle specific CMIT commands such as EXECUTE and POLL.
        """

        try:
            self.logger.debug("handling request")
            # Read raw request line (first line in request)
            self.raw_request_line = self.rfile.readline(_MAXLINE + 1)
            self.logger.debug(f"raw_request_line: {self.raw_request_line}")

            # If request line exceeds a maximum size, send error
            if len(self.raw_request_line) > _MAXLINE:
                self.request_line = ''
                self.request_version = ''
                self.command = ''
                self.send_error(CMITStatus.BAD_REQUEST)
                return

            # If request line is empty, assume connection closed
            if not self.raw_request_line:
                self.close_connection = True
                return

            # Commence parsing request
            if not self.parse_request():
                # if the parse_request function returned False,
                # it also sent an error message
                return

            # prepare the method name
            mname = 'do_' + self.command

            # check that method has been implemented on the server
            if not hasattr(self, mname):
                self.send_error(
                    CMITStatus.NOT_IMPLEMENTED,
                    "Unsupported method (%r)" % self.command
                )
                return

            self.logger.debug(f"parsing body")
            # retrieve data msg
            if not self.parse_body():
                return

            self.logger.debug(f"executing command: {mname}")
            # retrieve command method
            method = getattr(self, mname)

            # call command method
            method()

            # flush write file and send response
            self.wfile.flush()

        except socket.timeout as e:
            # a read or a write timed out.  Discard this connection
            self.log_error("Request timed out: %r", e)
            self.close_connection = True
            return

    def handle(self):
        """
        Handle multiple requests if necessary.
        """
        self.close_connection = True
        self.handle_one_request()

        while not self.close_connection:
            self.handle_one_request()

    def send_error(self, code, message=None, explain=None, topic=None, msg_id=None):
        """
        Send and log an error reply.

        This will send an error response, and therefore must be
        called before any other output is generated. First it logs
        the error, then it sends a :class:`ServerErrorMessage`
        formatted response to the client.

        :arg code: an CMIT error code (3 digits)
        :arg message: a simple optional 1 line response phrase.
            defaults to short entry matching the response code.
        :arg explain: a more detailed message.
            defaults to long entry matching response code.
        :arg topic: the topic of the errored request
        :arg msg_id: the msg_id of the errored request
        """

        try:
            short, long = self.responses[code]
        except KeyError:
            short, long = '???', '???'
        if message is None:
            message = short
        if explain is None:
            explain = long
        if topic is None:
            topic = f"error.{message}"
        if msg_id is None:
            msg_id = "%032x" % randbits(128)

        # Log the error
        self.log_error("code %d, message %s", code, message)

        # Prepare error_message_class
        msg = self.error_message_class(
            topic, msg_id, int(datetime.utcnow().timestamp()), code, f"{message} - {explain}"
        )

        # append status and reason to response
        self.send_response(code, message)

        # flush the response line
        self.flush_response_line()

        # write error message to response body
        self.wfile.write(msg())

    def send_response(self, code, message=None):
        """
        Add the response header to the headers buffer and log the
        response code.

        Also send two standard headers with the server software
        version and the current date.

        """

        # log request and response code
        self.log_request(code)
        self.send_response_status(code, message)

    # noinspection PyAttributeOutsideInit
    def send_response_status(self, code, message=None):
        """Send the response status line."""
        if message is None:
            if code in self.responses:
                message = self.responses[code][0]
            else:
                message = ''

        if not hasattr(self, '_response_buffer'):
            self._response_buffer = []

        self._response_buffer.append(
            ("%s %d %s\r\n" % (self.default_protocol_version, code, message)).encode('latin-1', 'strict')
        )

    def end_response_line(self):
        """
        Send the blank line ending the response line.
        """
        self._response_buffer.append(b"\r\n")
        self.flush_response_line()

    def flush_response_line(self):
        """
        Send the headers stored in the _headers_buffer.
        """
        if hasattr(self, '_response_buffer'):
            self.wfile.write(b"".join(self._response_buffer))
            self._response_buffer = []

    def log_request(self, code: Any = '-', msg: Any = '-'):
        """Log an accepted request.

        This is called by send_response().

        """
        if isinstance(code, CMITStatus):
            msg = code.phrase if msg == '-' else msg
            code = code.value

        self.log_message('"%s" %s %s', self.request_line, str(code), str(msg))

    def log_error(self, fmt, *args):
        """Log an error.

        This is called when a request cannot be fulfilled.  By
        default, it passes the message on to log_message().

        Arguments are the same as for log_message().

        XXX This should go to the separate error log.

        """

        self.log_message(fmt, *args)

    def log_message(self, fmt, *args):
        """Log an arbitrary message.

        This is used by all other logging functions.  Override
        it if you have specific logging wishes.

        The first argument, FORMAT, is a format string for the
        message to be logged.  If the format string contains
        any % escapes requiring parameters, they should be
        specified as subsequent arguments (it's just like
        printf!).

        The client ip and current date/time are prefixed to
        every message.

        Unicode control characters are replaced with escaped hex
        before writing the output to stderr.

        """

        message: str = fmt % args
        self.logger.info("%s - - [%s] %s\n" %
                         (self.server.server_address,
                          self.log_date_time_string(),
                          message.translate(self._control_char_table)))

    def version_string(self):
        """Return the server software version string."""
        return self.server_version + ' ' + self.sys_version

    @staticmethod
    def date_time_string(timestamp=None):
        """
        Return the current date and time formatted for the message data
        """
        if timestamp is None:
            timestamp = datetime.utcnow().timestamp()
        return datetime.fromtimestamp(timestamp)

    def log_date_time_string(self):
        """Return the current time formatted for logging."""
        now = time.time()
        year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
        s = "%02d/%3s/%04d %02d:%02d:%02d" % (
            day, self.month_names[month], year, hh, mm, ss)
        return s

    def address_string(self):
        """Return the client address."""

        return self.client_address

    @property
    def msg(self) -> CMITMessage:
        return getattr(self, "request_msg") if hasattr(self, "request_msg") else None

    @msg.setter
    def msg(self, value):

        if not isinstance(value, CMITMessage) and isinstance(value, (str, bytes)):
            self.logger.debug(f"Message needs to be converted.")
            value = CMITMessage(value)

        setattr(self, "request_msg", value)


class SimpleCMITRequestHandler(BaseCMITRequestHandler):
    """
    Simple CMIT request handler with just PING command.

    This serves the clients response back to it.
    """

    server_version = "SimpleCMIT/" + __version__

    @cmit_response
    def do_PING(self):
        """
        Serve a PING request.

        This serves the clients response back to it.
        """

        return CMITStatus.OK, self.msg

    @cmit_response
    def do_EXECUTE(self):
        """
        Handle the EXECUTE command.
        """

        msg = CMITMessage(self.msg.topic, self.msg.msg_id)
        msg.payload = {"res": "Processed"}

        return CMITStatus.ACCEPTED, msg

    @cmit_response
    def do_POLL(self):
        """
        Handle the POLL command
        """

        msg = CMITMessage(self.msg.topic, self.msg.msg_id)
        msg.payload = {"depth": 0}

        return CMITStatus.OK, msg


__all__ = ['BaseCMITRequestHandler']

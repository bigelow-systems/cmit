"""
CMIT Server Utilities
"""
import base64
import socket
from typing import Any, Callable


def create_connection(socket_fp, *, timeout=None):
    sock = None
    err = None
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, socket.IPPROTO_IP)
        sock.connect(socket_fp)
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
        raise OSError("Can't connect to %r" % socket_fp)


def encode(data, name='data') -> bytes:
    try:
        return data.encode('latin-1')
    except UnicodeEncodeError as err:
        raise UnicodeEncodeError(
            err.encoding,
            err.object,
            err.start,
            err.end,
            '%s (%.20r) is not valid Latin-1. Use %s.encode(\'utf-8\') '
            'if you want to send it encoded in UTF-8.' %
            (name.title(), data[err.start:err.end], name)) from None


def log_command(func):
    """
    Decorator to log the command being executed.
    """

    def wrapper(ref):
        command = getattr(ref, "command") if hasattr(ref, "command") else "UNKNOWN"
        ref.logger.debug(f"Received {command.upper()} request: {str(ref.msg)}")
        ref.logger.debug(f"Msg Type: {type(ref.msg)}")
        return func(ref)

    return wrapper


def cmit_response(func: Callable[[Any], list]):

    def wrapper(ref):

        if hasattr(ref, "logger"):
            command = getattr(ref, "command") if hasattr(ref, "command") else "UNKNOWN"
            ref.logger.debug(f"Received {command.upper()} request: {str(ref.msg)}")
            ref.logger.debug(f"Msg Type: {type(ref.msg)}")

        status, msg = func(ref)

        msg = f"{base64.b64encode(bytes(msg)).decode()}\r\n"

        ref.send_response(status)
        ref.end_response_line()
        ref.wfile.write(msg.encode())

    return wrapper


__all__ = ["create_connection", "encode", "log_command", "cmit_response"]

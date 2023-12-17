"""
cmit.requests.api
~~~~~~~~~~~~~~~~~~~~

This module implements the CMIT API.
"""

from os import PathLike

from cmit.requests import sessions


def request(command, socket_fp, topic, data=None, msg_args=None, msg_kwargs=None):
    """
    Send a request to the CMIT server.

    :param command: The CMIT command to send.
    :type command: str
    :param socket_fp: A file-like object to send the request to.
    :type socket_fp: str or PathLike
    :param topic: The topic to send in the request.
    :type topic: str
    :param data: The data to send in the request.
    :type data: str or dict
    :param msg_args: The positional arguments to send in the request.
    :type msg_args: list
    :param msg_kwargs: The keyword arguments to send in the request.
    :type msg_kwargs: dict
    :return: :class:`CMITResponse <CMITResponse>`
    :rtype: cmit.requests.Response

    Usage::

        >>> from cmit import requests
        >>> req = requests.request('PING', 'cmit://tmp/cmit.sock', 'test', 'test', [1, 2, 3], {'test': 'test'})
        >>> req
        <CMITResponse [200]>
    """

    with sessions.Session() as session:
        return session.request(command, socket_fp, topic, data, msg_args, msg_kwargs)


def ping(socket_fp, topic, data=None, msg_args=None, msg_kwargs=None):
    """
    Send a ping request to the CMIT server.

    :param socket_fp: A file-like object to send the request to.
    :type socket_fp: str or PathLike
    :param topic: The topic to send in the request.
    :type topic: str
    :param data: The data to send in the request.
    :type data: str or dict
    :param msg_args: The positional arguments to send in the request.
    :type msg_args: list
    :param msg_kwargs: The keyword arguments to send in the request.
    :type msg_kwargs: dict
    :return: :class:`CMITResponse <CMITResponse>`
    :rtype: cmit.requests.Response

    Usage::

        >>> from cmit import requests
        >>> req = requests.ping('cmit://tmp/cmit.sock', 'test')
        >>> req
        <CMITResponse [200]>
    """

    return request('PING', socket_fp, topic, data, msg_args, msg_kwargs)


def execute(socket_fp, topic, data=None, msg_args=None, msg_kwargs=None):
    """
    Send an execute request to the CMIT server.

    :param socket_fp: A file-like object to send the request to.
    :type socket_fp: str or PathLike
    :param topic: The topic to send in the request.
    :type topic: str
    :param data: The data to send in the request.
    :type data: str or dict
    :param msg_args: The positional arguments to send in the request.
    :type msg_args: list
    :param msg_kwargs: The keyword arguments to send in the request.
    :type msg_kwargs: dict
    :return: :class:`CMITResponse<CMITResponse>`
    :rtype: cmit.requests.Response

    Usage::

        >>> from cmit import requests
        >>> req = requests.execute('cmit://tmp/cmit.sock', 'test', 'test', [1, 2, 3], {'test': 'test'})
        >>> req
        <CMITResponse [202]>
    """

    return request('EXECUTE', socket_fp, topic, data, msg_args, msg_kwargs)


def poll(socket_fp, topic):
    """
    Send a poll request to the CMIT server.

    :param socket_fp: A file-like object to send the request to.
    :type socket_fp: str or PathLike
    :param topic: The topic to send in the request.
    :type topic: str
    :return: :class:`CMITResponse<CMITResponse>`
    :rtype: cmit.requests.Response

    Usage::

        >>> from cmit import requests
        >>> req = requests.poll('cmit://tmp/cmit.sock', 'test')
        >>> req
        <CMITResponse [200]>
    """

    return request('POLL', socket_fp, topic)


__all__ = ['request', 'ping', 'execute', 'poll']

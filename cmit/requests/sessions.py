import datetime
import time
from collections import OrderedDict

from cmit.requests.adapters import CMITAdapter
from cmit.requests.exceptions import InvalidSchema
from cmit.requests.models import PreparedRequest, Request


class Session:
    """
    A CMIT Client Session.

    Basic Usage::

        >>> import cmit.requests as requests
        >>> s = requests.Session()
        >>> s.ping('cmit://temp/echo.sock')
        <Response [200]>

    Or as a context manager::

        >>> with requests.Session() as s:
        ...     s.ping('cmit://temp/echo.sock')
        <Response [200]>
    """

    __attrs__ = [
        "adapters",
    ]

    def __init__(self):

        # Default connection adapters.
        self.adapters = OrderedDict()
        self.mount('cmit://', CMITAdapter())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __getstate__(self):
        state = {attr: getattr(self, attr, None) for attr in self.__attrs__}
        return state

    def __setstate__(self, state):
        for attr, value in state.items():
            setattr(self, attr, value)

    def prepare_request(self, request):
        """
        Constructs a :class:`PreparedRequest <PreparedRequest>` for transmission and returns it.

        :param request: :class:`Request`
        :return: :class:`PreparedRequest<PreparedRequest>`
        :rtype: cmit.requests.models.PreparedRequest
        """

        p = PreparedRequest()
        p.prepare(
            request.command, request.socket_path, request.topic, request.data, request.rpc_args, request.rpc_kwargs
        )
        return p

    def request(self, command, fp, topic, data=None, msg_args=None, msg_kwargs=None):

        req = Request(command=command.upper(), socket_path=fp, topic=topic, data=data,
                      rpc_args=msg_args, rpc_kwargs=msg_kwargs)

        prep = self.prepare_request(req)

        resp = self.send(prep)

        return resp

    def ping(self, fp):
        return self.request('PING', fp, 'ping')

    def execute(self, fp, topic, data=None, msg_args=None, msg_kwargs=None):
        return self.request('EXECUTE', fp, topic, data=data, msg_args=msg_args, msg_kwargs=msg_kwargs)

    def poll(self, fp, topic):
        return self.request('POLL', fp, topic)

    def send(self, prep, **kwargs):
        """
        Transmits the prepared request.

        :param prep: :class:`PreparedRequest<PreparedRequest>` to send.
        :type prep: cmit.requests.models.PreparedRequest
        :return: :class:`Response <Response>`
        :rtype: cmit.requests.models.Response
        """

        if isinstance(prep, Request):
            raise ValueError('You can only send PreparedRequests.')

        stream = kwargs.get("stream")

        # Get the appropriate adapter to use
        adapter = self.get_adapter(uri=prep.socket_path)

        start = time.time()

        # Send the request
        resp = adapter.send(prep, **kwargs)

        elapsed = time.time() - start
        resp.elapsed = datetime.timedelta(seconds=elapsed)

        return resp

    def get_adapter(self, uri):
        """
        Returns the appropriate connection adapter for the given URI.

        :param uri: URI being requested.
        :type uri: str
        :return: :class:`BaseAdapter <BaseAdapter>` object.
        :rtype: cmit.requests.adapters.BaseAdapter
        """

        for prefix, adapter in self.adapters.items():
            if uri.lower().startswith(prefix.lower()):
                return adapter

        raise InvalidSchema(f"No adapter found for URI {uri!r}")

    def close(self):
        """
        Closes all adapters and as such the session.
        """

        for v in self.adapters.values():
            v.close()

    def mount(self, prefix, adapter):
        """
        Registers a connection adapter to a prefix.

        Adapters are sorted in descending order by prefix length.

        :param prefix: Prefix identifier of the adapter.
        :type prefix: str
        :param adapter: :class:`BaseAdapter <BaseAdapter>` object.
        :type adapter: cmit.requests.adapters.BaseAdapter
        """

        self.adapters[prefix] = adapter
        keys_to_move = [k for k in self.adapters if len(k) < len(prefix)]

        for k in keys_to_move:
            self.adapters[k] = self.adapters.pop(k)


__all__ = ["Session"]

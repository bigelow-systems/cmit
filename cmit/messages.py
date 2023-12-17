"""
Type Helpers
"""

import base64
import json
from datetime import datetime
from typing import Union

from .typing import PayloadType, TopicType
from .utils import encode as _encode


class CMITMessage(object):
    """
    Base class for all messages sent to and from the CMIT protocol server.
    """

    __slots__ = ["timestamp", "msg_id", "_topic", "_payload"]

    def __init__(self, topic: TopicType, msg_id="0"):
        self.timestamp = datetime.utcnow()
        self.msg_id = msg_id
        self._payload = b""
        if isinstance(topic, bytes):
            self._topic = topic
        elif isinstance(topic, str):
            self._topic = _encode(topic, 'topic')
        else:
            self._topic = _encode(topic(), 'topic')

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.topic)

    def __str__(self):
        return self.as_string()

    def __bytes__(self):
        return self.as_bytes()

    def __call__(self, *args, **kwargs) -> bytes:
        return base64.b64encode(self.as_bytes())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return str(self) == str(other)
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def as_bytes(self):
        return _encode(self.as_string(), 'CMITP Message')

    def as_string(self, iso_date=False, indent=None):
        msg = {
            "_id": self.msg_id,
            "timestamp": self.posix_timestamp if not iso_date else self.iso_timestamp,
            "topic": self.topic,
            "payload": self.payload
        }

        return json.dumps(msg, indent=indent)

    @classmethod
    def parse_message(cls, msg: Union[bytes, str]) -> "CMITMessage":
        msg_keys = ('_id',  'topic', 'timestamp', 'payload')

        try:
            decoded_msg = json.loads(base64.b64decode(msg).decode().strip())

            if isinstance(decoded_msg["payload"], str) and decoded_msg["payload"].startswith("{"):
                decoded_msg["payload"] = json.loads(decoded_msg["payload"])

        except json.JSONDecodeError as jde:
            raise ValueError(f"Invalid message:\n{msg}") from jde

        missing_keys = []
        for k in msg_keys:
            if k not in decoded_msg:
                missing_keys.append(k)

        if len(missing_keys) > 0:
            error_msg = "Keys missing from msg: " + ", ".join([str(mk) for mk in missing_keys])
            raise ValueError(error_msg)

        m = cls(decoded_msg["topic"], msg_id=decoded_msg["_id"])
        m.payload = decoded_msg["payload"]
        m.timestamp = datetime.fromtimestamp(decoded_msg["timestamp"])
        return m

    @property
    def iso_timestamp(self):
        return self.timestamp.isoformat()

    @property
    def topic(self):
        return self._topic.decode("utf-8")

    @topic.setter
    def topic(self, value: TopicType):
        try:
            if isinstance(value, str):
                topic = _encode(value, 'topic')
            elif isinstance(value, bytes):
                topic = value
            else:
                topic = _encode(value(), 'topic')

        except TypeError:
            raise TypeError(
                "topic should be a str, bytes, or a callable, "
                "got %r" % type(value)
            )

        self._topic = topic

    @property
    def payload(self):
        return self._payload.decode("utf-8")

    @payload.setter
    def payload(self, value: PayloadType):
        try:
            if isinstance(value, str):
                payload = _encode(value, 'payload')
            elif isinstance(value, bytes):
                payload = value
            elif callable(value):
                payload = _encode(value(), 'payload')
            else:
                payload = _encode(json.dumps(value), 'payload')

        except TypeError:
            raise TypeError(
                "payload should be a str, bytes, or a callable, "
                "got %r" % type(value)
            )

        self._payload = payload

    @property
    def posix_timestamp(self):
        return self.timestamp.timestamp()


# noinspection PyPep8Naming
class ServerErrorMessage(CMITMessage):

    def __init__(self, topic: str, msg_id: str, ts: int, code: int, reason: str):
        super().__init__(topic, msg_id=msg_id)
        self.timestamp = datetime.fromtimestamp(ts)
        self.payload = json.dumps({
            "code": code,
            "reason": reason
        })


__all__ = ["CMITMessage", "ServerErrorMessage"]

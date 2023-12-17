
import re
import typing

_SCHEME_RE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+-]*:|/)")
_URI_RE = re.compile(
    r"^(?:([a-zA-Z][a-zA-Z0-9+.-]*):)?"
    r"(?://([^\\?#.]*))?"
    r"([^?#]*)$",
    re.UNICODE | re.DOTALL,
)


_SocketPathBase = typing.NamedTuple(
    "SocketPath",
    [("scheme", typing.Optional[str]), ("path", typing.Optional[str]), ("file_type", typing.Optional[str])]
)


class SocketPath(_SocketPathBase):
    def __new__(cls, scheme=None, path=None, file_type=None):
        if scheme is not None:
            scheme = scheme.lower()
        if path and not path.startswith("/"):
            path = "/" + path
        return super().__new__(cls, scheme, path, file_type)

    @property
    def socket_path(self):
        return self.path + self.file_type


def to_native_str(s, encoding='ascii') -> str:

    if isinstance(s, bytes):
        return s.decode(encoding)
    else:
        return s


def parse_socket_path(socket_path: str) -> SocketPath:

    if not socket_path:
        return SocketPath()

    source = socket_path

    if not _SCHEME_RE.search(socket_path):
        socket_path = "//" + socket_path

    try:
        scheme, path, file_type = _URI_RE.match(socket_path).groups()
        normalized_scheme = scheme is None or scheme.lower() in ("cmit", "unix", None)

        if scheme:
            scheme = scheme.lower()

    except (AttributeError, ValueError) as e:
        raise ValueError(f"Invalid CMIT Path {source!r}") from e

    if not file_type:
        file_type = ".sock"

    return SocketPath(scheme, path, file_type)


__all__ = ["parse_socket_path", "SocketPath", "to_native_str"]

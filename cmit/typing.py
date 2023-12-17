"""
Type Helpers
"""

from typing import Callable, Union


TopicType = Union[str, bytes, Callable[[], str]]
PayloadType = Union[str, dict, bytes, Callable[[], str]]


__all__ = ["PayloadType", "TopicType"]

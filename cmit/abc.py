"""
Abstract and low level classes and functions.
"""

import itertools
import socketserver


class _BaseStreamRequestHandler(socketserver.StreamRequestHandler):
    wbufsize = -1

    month_names = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    _control_char_table = str.maketrans(
        {c: fr'\x{c:02x}' for c in itertools.chain(range(0x20), range(0x7f, 0xa0))})

    _control_char_table[ord('\\')] = r'\\'


__all__ = ["_BaseStreamRequestHandler"]

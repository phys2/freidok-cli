import contextlib
import sys
from typing import Callable, TypeVar

T = TypeVar('T')


def list2str(items: list | None, sep: str = ',') -> str | None:
    """Convert a list to a string"""
    if items is None:
        return None
    else:
        return sep.join([str(item) for item in items])


def str2list(arg: str, mapper: Callable[[str], T] = str, sep: str = ',') -> list[T]:
    """Convert a string to a list with optional modifier"""
    items = arg.strip().strip(sep).split(sep)
    return [mapper(item.strip()) for item in items]


@contextlib.contextmanager
def opens(file=None, mode='w', stream=sys.stdout, **kwargs):
    """Open file for writing, otherwise use stream"""
    if file and file != '-':
        fh = open(file, mode, **kwargs)
    else:
        fh = stream

    try:
        yield fh
    finally:
        if fh is not stream:
            fh.close()

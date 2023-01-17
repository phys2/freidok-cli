import contextlib
import sys
from typing import Iterable, Callable, TypeVar

T = TypeVar('T')


def list2str(items: list | None, sep: str = ',') -> str | None:
    if items is None:
        return None
    else:
        return sep.join([str(item) for item in items])


def str2list(arg: str, mapper: Callable[[str], T] = str, sep: str = ',') -> list[T]:
    items = arg.strip().strip(sep).split(sep)
    return [mapper(item.strip()) for item in items]


def first(it: Iterable[T], predicate: Callable[[T], bool],
          default: T | None = None) -> T | None:
    """Return first element from iterable that fulfills the predicate"""
    return next((x for x in it if predicate(x)), default)


def firstindex(it: Iterable[T], predicate: Callable[[T], bool]) -> int:
    for i, item in it:
        if predicate(item):
            return i
    return -1


def movetofront(listobj: list[T], predicate: Callable[[T], bool]):
    i = first(listobj, predicate)
    if i > 0:
        item = listobj.pop(i)
        listobj.insert(0, item)


def preference_score(value, preferred_values: list):
    """Return index of value in list of preferred values"""
    try:
        return preferred_values.index(value)
    except ValueError:
        return len(preferred_values) + 1


@contextlib.contextmanager
def opens(file=None, mode='w', stream=sys.stdout, **kwargs):
    """Open file for writing or fall back to stream"""
    if file and file != '-':
        fh = open(file, mode, **kwargs)
    else:
        fh = stream

    try:
        yield fh
    finally:
        if fh is not stream:
            fh.close()

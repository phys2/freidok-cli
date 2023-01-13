from typing import Iterable, Callable, TypeVar

T = TypeVar('T')


def list2str(items: list | None, sep: str = ',') -> str | None:
    if items is None:
        return None
    else:
        return sep.join([str(item) for item in items])


def str2list(arg: str, mapper: Callable = str):
    return [mapper(item.strip()) for item in arg.split(',')]


def first(it: Iterable[T], predicate: Callable[[T], bool],
          default: T | None = None) -> T | None:
    """Return first element from iterable that fulfills the predicate"""
    return next((x for x in it if predicate(x)), default)

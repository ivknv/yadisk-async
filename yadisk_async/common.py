# -*- coding: utf-8 -*-

import datetime

from .compat import Callable, List, AsyncIterable

from typing import Optional, TypeVar, Any, Union, IO, Protocol

__all__ = ["typed_list", "int_or_error", "str_or_error", "bool_or_error",
           "dict_or_error", "str_or_dict_or_error", "yandex_date", "is_operation_link",
           "is_resource_link", "is_public_resource_link", "ensure_path_has_schema",
           "FileOrPath", "FileOrPathDestination", "CaseInsensitiveDict"]

T = TypeVar("T", bound=Callable)

def typed_list(datatype: T) -> Callable[[Optional[List]], List[T]]:
    def list_factory(iterable: Optional[List] = None) -> List[T]:
        if iterable is None:
            return []

        if not isinstance(iterable, list):
            raise ValueError(f"Expected a list, got {type(iterable)}")

        return [datatype(i) for i in iterable]

    return list_factory

def int_or_error(x: Any) -> int:
    if not isinstance(x, int):
        raise ValueError(f"{repr(x)} is not an integer")

    return x

def str_or_error(x: Any) -> str:
    if not isinstance(x, str):
        raise ValueError(f"{repr(x)} is not a string")

    return x

def bool_or_error(x: Any) -> bool:
    if not isinstance(x, bool):
        raise ValueError(f"{repr(x)} is not a boolean value")

    return x

def dict_or_error(x: Any) -> dict:
    if not isinstance(x, dict):
        raise ValueError(f"{repr(x)} is not a dict")

    return x

def str_or_dict_or_error(x: Any) -> Union[str, dict]:
    if not isinstance(x, (str, dict)):
        raise ValueError(f"{repr(x)} is not a string nor a dict")

    return x

def yandex_date(string):
    return datetime.datetime.strptime(string[:-3] + string[-2:], "%Y-%m-%dT%H:%M:%S%z")

def is_operation_link(link: str) -> bool:
    if link.startswith("https://cloud-api.yandex.net/v1/disk/operations/"):
        return True

    # Same but http:// version
    return link.startswith("http://cloud-api.yandex.net/v1/disk/operations/")

def is_resource_link(url: str) -> bool:
    if url.startswith("https://cloud-api.yandex.net/v1/disk/resources?"):
        return True

    # Check also for HTTP version
    return url.startswith("http://cloud-api.yandex.net/v1/disk/resources?")

def is_public_resource_link(url: str) -> bool:
    if url.startswith("https://cloud-api.yandex.net/v1/disk/public/resources?"):
        return True

    # Check also for HTTP version
    return url.startswith("http://cloud-api.yandex.net/v1/disk/public/resources?")

def ensure_path_has_schema(path: str, default_schema: str = "disk") -> str:
    # Modifies path to always have a schema (disk:/, trash:/ or app:/).
    # Without the schema Yandex.Disk won't let you upload filenames with the ':' character.
    # See https://github.com/ivknv/yadisk/issues/26 for more details

    KNOWN_SCHEMAS = ("disk:", "trash:", "app:")

    if path in KNOWN_SCHEMAS:
        return default_schema + ":/" + path

    if path.startswith("/"):
        return default_schema + ":" + path

    if any(path.startswith(schema + "/") for schema in KNOWN_SCHEMAS):
        return path

    return default_schema + ":/" + path

class AsyncFileLike(Protocol):
    async def read(self, size: int = ..., /) -> Union[str, bytes]: ...
    async def write(self, buffer: Any, /) -> int: ...
    async def seek(self, pos: int, whence: int = ..., /) -> int: ...
    async def tell(self) -> int: ...

class BinaryAsyncFileLike(Protocol):
    async def read(self, size: int = ..., /) -> bytes: ...
    async def write(self, buffer: Any, /) -> int: ...
    async def seek(self, pos: int, whence: int = ..., /) -> int: ...
    async def tell(self) -> int: ...

FileOrPath = Union[
    str,
    bytes,
    IO,
    AsyncFileLike,
    Callable[[], AsyncIterable[bytes]]]

FileOrPathDestination = Union[
    str,
    bytes,
    IO[bytes],
    BinaryAsyncFileLike]

# https://stackoverflow.com/a/32888599/3653520
class CaseInsensitiveDict(dict):
    K = TypeVar("K")

    @classmethod
    def _k(cls, key: K) -> K:
        return key.lower() if isinstance(key, str) else key

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._convert_keys()

    def __getitem__(self, key: K) -> Any:
        return super().__getitem__(self.__class__._k(key))

    def __setitem__(self, key: K, value: Any) -> None:
        super().__setitem__(self.__class__._k(key), value)

    def __delitem__(self, key: K) -> Any:
        return super().__delitem__(self.__class__._k(key))

    def __contains__(self, key: K) -> bool:
        return super().__contains__(self.__class__._k(key))

    def pop(self, key: K, /, *args, **kwargs) -> Any:
        return super().pop(self.__class__._k(key), *args, **kwargs)

    def get(self, key: K, /, *args, **kwargs) -> Any:
        return super().get(self.__class__._k(key), *args, **kwargs)

    def setdefault(self, key: K, *args, **kwargs) -> Any:
        return super().setdefault(self.__class__._k(key), *args, **kwargs)

    def update(self, E: dict = {}, **F) -> None:
        super().update(self.__class__(E))
        super().update(self.__class__(**F))

    def _convert_keys(self) -> None:
        for k in list(self.keys()):
            v = super(CaseInsensitiveDict, self).pop(k)
            self.__setitem__(k, v)

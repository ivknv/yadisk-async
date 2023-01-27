# -*- coding: utf-8 -*-

__all__ = ["List", "Dict", "Set", "Callable", "Iterable", "Generator",
           "AsyncGenerator", "Coroutine", "Awaitable", "TimeoutError"]

import sys

if sys.version_info.major == 3 and sys.version_info.minor < 9:
    from typing import (
        List, Dict, Set, Callable, Iterable, Generator, AsyncGenerator,
        Coroutine, Awaitable
    )
else:
    from collections.abc import (
        Callable, Iterable, Generator,AsyncGenerator, Coroutine, Awaitable
    )

    List = list
    Dict = dict
    Set = set

if sys.version_info.major == 3 and sys.version_info.minor < 11:
    from asyncio import TimeoutError
else:
    TimeoutError = TimeoutError

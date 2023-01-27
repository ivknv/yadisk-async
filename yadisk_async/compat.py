# -*- coding: utf-8 -*-

__all__ = ["List", "Dict", "Set", "Callable", "Iterable", "Generator", "AsyncGenerator"]

import sys

if sys.version_info.major == 3 and sys.version_info.minor < 9:
    from typing import List, Dict, Set, Callable, Iterable, Generator
    from typing import AsyncGenerator
else:
    from collections.abc import Callable, Iterable, Generator, AsyncGenerator

    List = list
    Dict = dict
    Set = set

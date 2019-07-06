# -*- coding: utf-8 -*-

import sys
import aiohttp

from .common import CaseInsensitiveDict

__all__ = ["SessionWithHeaders"]

DEFAULT_USER_AGENT = "Python/%s.%s aiohttp/%s" % (sys.version_info.major,
                                                  sys.version_info.minor,
                                                  aiohttp.__version__)

class SessionWithHeaders(aiohttp.ClientSession):
    """Just like your regular :any:`aiohttp.ClientSession` but with headers"""

    def __init__(self, *args, **kwargs):
        aiohttp.ClientSession.__init__(self, *args, **kwargs)

        self.headers = CaseInsensitiveDict({
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept-Encoding": ", ".join(("gzip", "deflate")),
            "Accept": "*/*",
            "Connection": "keep-alive"
        })

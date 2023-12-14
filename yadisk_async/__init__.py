# -*- coding: utf-8 -*-

from . import api, objects, exceptions, utils
from .yadisk import YaDisk

import warnings

__version__ = "1.4.5"

warnings.warn("This library is no longer maintained, use yadisk>=2.0.0 instead, it supports async API", DeprecationWarning)

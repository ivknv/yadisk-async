
Documentation
=============

.. autoclass:: yadisk_async.YaDisk
   :members:

General parameters
##################

Almost all methods of `YaDisk` (the ones that accept `**kwargs`) accept some additional arguments:

* **n_retries** - `int`, maximum number of retries for a request
* **retry_delay** - `float`, delay between retries (in seconds)
* **headers** - `dict` or `None`, additional request headers

`aiohttp` parameters like `timeout`, `proxies`, etc. are also accepted (see :py:func:`aiohttp.request`).

This also applies to low-level functions and API request objects as well.

Settings
########

The following settings can be accessed and changed at runtime in `yadisk_async.settings` module:

* **DEFAULT_TIMEOUT** - :py:class:`aiohttp.ClientTimeout`, default timeout for requests.
* **DEFAULT_N_RETRIES** - `int`, default number of retries
* **DEFAULT_RETRY_INTERVAL** - `float`, default retry interval
* **DEFAULT_UPLOAD_TIMEOUT** - analogous to `DEFAULT_TIMEOUT` but for `upload` function
* **DEFAULT_UPLOAD_RETRY_INTERVAL** - analogous to `DEFAULT_RETRY_INTERVAL` but for `upload` function

Exceptions
##########

Aside from the exceptions listed below, API requests can also raise exceptions in `aiohttp`.

.. automodule:: yadisk_async.exceptions
   :members:
   :show-inheritance:

Objects
#######

.. automodule:: yadisk_async.objects

   .. autoclass:: YaDiskObject
      :members:

   .. autoclass:: ErrorObject
      :members:
      :show-inheritance:

.. automodule:: yadisk_async.objects.auth
   :members:
   :show-inheritance:

.. automodule:: yadisk_async.objects.disk
   :members:
   :show-inheritance:

.. automodule:: yadisk_async.objects.resources
   :members:
   :show-inheritance:

.. automodule:: yadisk_async.objects.operations
   :members:
   :show-inheritance:

Low-level API
#############

Utilities
*********

.. automodule:: yadisk_async.utils
   :members:

Functions
*********

.. automodule:: yadisk_async.functions.auth
   :members:

.. automodule:: yadisk_async.functions.disk
   :members:

.. automodule:: yadisk_async.functions.resources
   :members:

.. automodule:: yadisk_async.functions.operations
   :members:

API request objects
*******************

.. automodule:: yadisk_async.api

   .. autoclass:: APIRequest
      :members:

.. automodule:: yadisk_async.api.auth
   :members:
   :show-inheritance:

.. automodule:: yadisk_async.api.disk
   :members:
   :show-inheritance:

.. automodule:: yadisk_async.api.resources
   :members:
   :show-inheritance:

.. automodule:: yadisk_async.api.operations
   :members:
   :show-inheritance:

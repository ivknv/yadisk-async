YaDisk-async
============

.. image:: https://img.shields.io/readthedocs/yadisk-async.svg
   :alt: Read the Docs
   :target: https://yadisk-async.readthedocs.io/en/latest/

.. image:: https://img.shields.io/pypi/v/yadisk-async.svg
   :alt: PyPI
   :target: https://pypi.org/project/yadisk-async

YaDisk-async is a Yandex.Disk REST API client library with async/await support.

.. _Read the Docs (EN): http://yadisk-async.readthedocs.io
.. _Read the Docs (RU): http://yadisk-async.readthedocs.io/ru/latest

Documentation is available at `Read the Docs (EN)`_ and `Read the Docs (RU)`_.

Installation
************

.. code:: bash

    pip install yadisk-async

or

.. code:: bash

    python setup.py install

Examples
********

.. code:: python

    import yadisk_async

    y = yadisk_async.YaDisk(token="<token>")
    # or
    # y = yadisk_async.YaDisk("<application-id>", "<application-secret>", "<token>")

    # Check if the token is valid
    print(await y.check_token())

    # Get disk information
    print(await y.get_disk_info())

    # Print files and directories at "/some/path"
    print([i async for i in await y.listdir("/some/path")])

    # Upload "file_to_upload.txt" to "/destination.txt"
    await y.upload("file_to_upload.txt", "/destination.txt")

    # Same thing
    async with aiofiles.open("file_to_upload.txt", "rb") as f:
        await y.upload(f, "/destination.txt")

    # Same thing but with regular files
    with open("file_to_upload.txt", "rb") as f:
        await y.upload(f, "/destination.txt")

    # Download "/some-file-to-download.txt" to "downloaded.txt"
    await y.download("/some-file-to-download.txt", "downloaded.txt")

    # Same thing
    async with aiofiles.open("downloaded.txt", "wb") as f:
        await y.download("/some-file-to-download.txt", f)

    # Permanently remove "/file-to-remove"
    await y.remove("/file-to-remove", permanently=True)

    # Create a new directory at "/test-dir"
    print(await y.mkdir("/test-dir"))

    # Always remember to close all the connections or you'll get a warning
    await y.close()

Changelog
*********

.. _yadisk: https://github.com/ivknv/yadisk

.. _issue #2: https://github.com/ivknv/yadisk/issues/2
.. _issue #4: https://github.com/ivknv/yadisk/issues/4
.. _issue #7: https://github.com/ivknv/yadisk/issues/7
.. _PR #1: https://github.com/ivknv/yadisk-async/pull/1
.. _issue #23: https://github.com/ivknv/yadisk/issues/23
.. _PR #6: https://github.com/ivknv/yadisk-async/pull/6
.. _issue #26: https://github.com/ivknv/yadisk/issues/26
.. _issue #28: https://github.com/ivknv/yadisk/issues/28
.. _issue #29: https://github.com/ivknv/yadisk/issues/29
.. _PR #31: https://github.com/ivknv/yadisk/pull/31

* **Release 1.4.4 (2023-10-15)**

  * :code:`upload()` and :code:`download()` (and related) methods can now
    upload/download non-seekable file-like objects (e.g. :code:`stdin` or :code:`stdout`
    when open in binary mode), see `PR #31`_

* **Release 1.4.3 (2023-04-22)**

  * :code:`app:/` paths now work correctly (see `issue #26`_)

* **Release 1.4.2 (2023-03-20)**

  * Fixed `issue #29`_: TypeError: 'type' object is not subscriptable
  * Fixed a bug affecting Python <3.9: TypeError: Too many parameters for typing.AsyncIterable; actual 2, expected 1

* **Release 1.4.1 (2023-02-28)**

  * Fixed `issue #28`_: calling :code:`download_public()` with :code:`path` keyword argument raises :code:`TypeError`
  * Fixed :code:`AttributeError` raised when calling :code:`ResourceLinkObject.public_listdir()`

* **Release 1.4.0 (2023-01-30)**

  * Added convenience methods to :code:`...Object` objects (e.g. see :code:`ResourceObject` in docs)
  * Added type hints
  * Improved error checking and response validation
  * Added :code:`InvalidResponseError`, :code:`PayloadTooLargeError`, :code:`UploadTrafficLimitExceededError`
  * Added a few missing fields to :code:`DiskInfoObject` and :code:`SystemFoldersObject`
  * Added :code:`rename()`, :code:`upload_by_link()` and :code:`download_by_link()` methods
  * Added :code:`default_args` field for :code:`YaDisk` object
  * :code:`download()` and :code:`upload()` now return :code:`ResourceLinkObject`
  * Returned :code:`LinkObject` instances have been replaced by more specific subclasses
  * :code:`TimeoutError` now also triggers a retry
  * Added support for async files for :code:`download()` and :code:`upload()`
  * Use :code:`aiofiles` to open files by default

* **Release 1.3.6 (2023-01-20)**

  * Fixed `issue #26`_: ':' character in filenames causes :code:`BadRequestError`.
    This is due the behavior of Yandex.Disk's REST API itself but is avoided
    on the library level with this fix.

* **Release 1.3.5 (2022-11-10)**

  * Fixed a bug in :code:`is_file()` and :code:`is_dir()`: a typo was causing
    :code:`AttributeError` (`PR #6`_).

* **Release 1.3.4 (2022-08-17)**

  * Fixed a bug in :code:`check_token()`: could throw :code:`ForbiddenError` if
    the application lacks necessary permissions (`issue #23`_).

* **Release 1.3.3 (2021-12-31)**

  * Fixed an issue where :code:`http://` links were not recognized as operation links
    (they were assumed to always be :code:`https://`, since all the other
    requests are always HTTPS).
    Occasionally, Yandex.Disk can for some reason return an :code:`http://` link
    to an asynchronous operation instead of :code:`https://`.
    Both links are now recognized correctly and an :code:`https://` version will
    always be used by :code:`get_operation_status()`, regardless of which one
    Yandex.Disk returned.

* **Release 1.3.2 (2021-07-10)**

  * Fixed :code:`__version__` having the old value

* **Release 1.3.1 (2021-07-10)**

  * Fixed :code:`AttributeError` in :code:`SessionWithHeaders` (`PR #1`_)
  * Fixed trash bin tests

* **Release 1.3.0 (2019-07-06)**

  * Modified the original library (`yadisk`_) to support `async/await`
  * The library was renamed to `yadisk-async`

The following releases are for `yadisk`_, the original library:

* **Release 1.2.14 (2019-03-26)**

  * Fixed a :code:`TypeError` in :code:`get_public_*` functions when passing :code:`path` parameter
    (see `issue #7`_)
  * Added :code:`unlimited_autoupload_enabled` attribute for :code:`DiskInfoObject`

* **Release 1.2.13 (2019-02-23)**

  * Added :code:`md5` parameter for :code:`remove()`
  * Added :code:`UserPublicInfoObject`
  * Added :code:`country` attribute for :code:`UserObject`
  * Added :code:`photoslice_time` attribute for :code:`ResourceObject`, :code:`PublicResourceObject`
    and :code:`TrashResourceObject`

* **Release 1.2.13 (2019-02-23)**

  * Added :code:`md5` parameter for :code:`remove()`
  * Added :code:`UserPublicInfoObject`
  * Added :code:`country` attribute for :code:`UserObject`
  * Added :code:`photoslice_time` attribute for :code:`ResourceObject`, :code:`PublicResourceObject`
    and :code:`TrashResourceObject`

* **Release 1.2.12 (2018-10-11)**

  * Fixed `fields` parameter not working properly in `listdir()` (`issue #4`_)

* **Release 1.2.11 (2018-06-30)**

  * Added the missing parameter :code:`sort` for :code:`get_meta()`
  * Added :code:`file` and :code:`antivirus_status` attributes for :code:`ResourceObject`,
    :code:`PublicResourceObject` and :code:`TrashResourceObject`
  * Added :code:`headers` parameter
  * Fixed a typo in :code:`download()` and :code:`download_public()` (`issue #2`_)
  * Removed :code:`*args` parameter everywhere

* **Release 1.2.10 (2018-06-14)**

  * Fixed :code:`timeout=None` behavior. :code:`None` is supposed to mean 'no timeout' but
    in the older versions it was synonymous with the default timeout.

* **Release 1.2.9 (2018-04-28)**

  * Changed the license to LGPLv3 (see :code:`COPYING` and :code:`COPYING.lesser`)
  * Other package info updates

* **Release 1.2.8 (2018-04-17)**

  * Fixed a couple of typos: :code:`PublicResourceListObject.items` and
    :code:`TrashResourceListObject.items` had wrong types
  * Substitute field aliases in :code:`fields` parameter when performing
    API requests (e.g. :code:`embedded` -> :code:`_embedded`)

* **Release 1.2.7 (2018-04-15)**

  * Fixed a file rewinding bug when uploading/downloading files after a retry

* **Release 1.2.6 (2018-04-13)**

  * Now caching :code:`requests` sessions so that open connections
    can be reused (which can significantly speed things up sometimes)
  * Disable :code:`keep-alive` when uploading/downloading files by default

* **Release 1.2.5 (2018-03-31)**

  * Fixed an off-by-one bug in :code:`utils.auto_retry()`
    (which could sometimes result in :code:`AttributeError`)
  * Retry the whole request for :code:`upload()`, :code:`download()` and :code:`download_public()`
  * Set :code:`stream=True` for :code:`download()` and :code:`download_public()`
  * Other minor fixes

* **Release 1.2.4 (2018-02-19)**

  * Fixed :code:`TokenObject` having :code:`exprires_in` instead of :code:`expires_in` (fixed a typo)

* **Release 1.2.3 (2018-01-20)**

  * Fixed a :code:`TypeError` when :code:`WrongResourceTypeError` is raised

* **Release 1.2.2 (2018-01-19)**

  * :code:`refresh_token()` no longer requires a valid or empty token.

* **Release 1.2.1 (2018-01-14)**

  * Fixed auto retries not working. Whoops.

* **Release 1.2.0 (2018-01-14)**

  * Fixed passing :code:`n_retries=0` to :code:`upload()`,
    :code:`download()` and :code:`download_public()`
  * :code:`upload()`, :code:`download()` and :code:`download_public()`
    no longer return anything (see the docs)
  * Added :code:`utils` module (see the docs)
  * Added :code:`RetriableYaDiskError`, :code:`WrongResourceTypeError`,
    :code:`BadGatewayError` and :code:`GatewayTimeoutError`
  * :code:`listdir()` now raises :code:`WrongResourceTypeError`
    instead of :code:`NotADirectoryError`

* **Release 1.1.1 (2017-12-29)**

  * Fixed argument handling in :code:`upload()`, :code:`download()` and :code:`download_public()`.
    Previously, passing :code:`n_retries` and :code:`retry_interval` would raise an exception (:code:`TypeError`).

* **Release 1.1.0 (2017-12-27)**

  * Better exceptions (see the docs)
  * Added support for :code:`force_async` parameter
  * Minor bug fixes

* **Release 1.0.8 (2017-11-29)**

  * Fixed yet another :code:`listdir()` bug

* **Release 1.0.7 (2017-11-04)**

  * Added :code:`install_requires` argument to :code:`setup.py`

* **Release 1.0.6 (2017-11-04)**

  * Return :code:`OperationLinkObject` in some functions

* **Release 1.0.5 (2017-10-29)**

  * Fixed :code:`setup.py` to exclude tests

* **Release 1.0.4 (2017-10-23)**

  * Fixed bugs in :code:`upload`, :code:`download` and :code:`listdir` functions
  * Set default :code:`listdir` :code:`limit` to :code:`10000`

* **Release 1.0.3 (2017-10-22)**

  * Added settings

* **Release 1.0.2 (2017-10-19)**

  * Fixed :code:`get_code_url` function (added missing parameters)

* **Release 1.0.1 (2017-10-18)**

  * Fixed a major bug in :code:`GetTokenRequest` (added missing parameter)

* **Release 1.0.0 (2017-10-18)**

  * Initial release

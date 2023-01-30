YaDisk-async
============

.. image:: https://img.shields.io/readthedocs/yadisk-async.svg
   :alt: Read the Docs
   :target: https://yadisk-async.readthedocs.io/en/latest/

.. image:: https://img.shields.io/pypi/v/yadisk-async.svg
   :alt: PyPI
   :target: https://pypi.org/project/yadisk-async

YaDisk-async - это библиотека-клиент REST API Яндекс.Диска с поддержкой async/await.

.. _Read the Docs (EN): http://yadisk-async.readthedocs.io
.. _Read the Docs (RU): http://yadisk-async.readthedocs.io/ru/latest

Документация доступна на `Read the Docs (RU)`_ и `Read the Docs (EN)`_.

Установка
*********

.. code:: bash

    pip install yadisk-async

или

.. code:: bash

    python setup.py install

Примеры
*******

.. code:: python

    import yadisk_async

    y = yadisk_async.YaDisk(token="<token>")
    # или
    # y = yadisk_async.YaDisk("<id-приложения>", "<secret-приложения>", "<токен>")

    # Проверяет, валиден ли токен
    print(await y.check_token())

    # Получает общую информацию о диске
    print(await y.get_disk_info())

    # Выводит содержимое "/some/path"
    print([i async for i in await y.listdir("/some/path")])

    # Загружает "file_to_upload.txt" в "/destination.txt"
    await y.upload("file_to_upload.txt", "/destination.txt")

    # То же самое
    with open("file_to_upload.txt", "rb") as f:
        await y.upload(f, "/destination.txt")

    # То же самое, но с aiofiles
    async with aiofiles.open("file_to_upload.txt", "rb") as f:
        await y.upload(f, "/destination.txt")

    # Скачивает "/some-file-to-download.txt" в "downloaded.txt"
    await y.download("/some-file-to-download.txt", "downloaded.txt")

    # То же самое, но с aiofiles
    async with aiofiles.open("downloaded.txt", "wb") as f:
        await y.download("/some-file-to-download.txt", f)

    # Безвозвратно удаляет "/file-to-remove"
    await y.remove("/file-to-remove", permanently=True)

    # Создаёт новую папку "/test-dir"
    print(await y.mkdir("/test-dir"))

    # Всегда закрывайте все соединения или получите предупреждение
    await y.close()

История изменений
*****************

.. _yadisk: https://github.com/ivknv/yadisk

.. _issue #2: https://github.com/ivknv/yadisk/issues/2
.. _issue #4: https://github.com/ivknv/yadisk/issues/4
.. _issue #7: https://github.com/ivknv/yadisk/issues/7
.. _PR #1: https://github.com/ivknv/yadisk-async/pull/1
.. _issue #23: https://github.com/ivknv/yadisk/issues/23
.. _PR #6: https://github.com/ivknv/yadisk-async/pull/6
.. _issue #26: https://github.com/ivknv/yadisk/issues/26

* **Release 1.4.0 (2023-01-30)**

  * Добавлены convenience-методы для объектов :code:`...Object` (например, см. :code:`ResourceObject`)
  * Добавлены подсказки типов (type hints)
  * Улучшены проверки ошибок и проверка ответа
  * Добавлены :code:`InvalidResponseError`, :code:`PayloadTooLargeError`, :code:`UploadTrafficLimitExceededError`
  * Добавлено несколько недостающих полей объектов :code:`DiskInfoObject` и :code:`SystemFoldersObject`
  * Добавлены методы :code:`rename()`, :code:`upload_by_link()` и :code:`download_by_link()`
  * Добавлен аттрибут :code:`default_args` объекта :code:`YaDisk`
  * :code:`download()` и :code:`upload()` теперь возвращают :code:`ResourceLinkObject`
  * До этого возвращаемые объекты :code:`LinkObject` были заменены более конкретными подклассами
  * :code:`TimeoutError` теперь тоже вызывает повторную попытку
  * Добавлена поддержка асинхронных файлов для :code:`download()` и :code:`upload()`
  * По умолчанию используется библиотека :code:`aiofiles` для открытия файлов

* **Release 1.3.6 (2023-01-20)**

  * Исправлено `issue #26`_: символ ':' в именах файлов приводит к
    :code:`BadRequestError`. Это поведение вызвано работой самого REST API
    Яндекс.Диска, но было исправлено на уровне библиотеки.

* **Release 1.3.5 (2022-11-10)**

  * Исправлен баг в :code:`is_file()` и :code:`is_dir()`: из-за опечатки функции
    вызывали исключение :code:`AttributeError` (`PR #6`_).

* **Release 1.3.4 (2022-08-17)**

  * Исправлен баг в :code:`check_token()`: функция могла вызвать :code:`ForbiddenError`,
    если у приложения недостатчно прав (`issue #23`_).

* **Release 1.3.3 (2021-12-31)**

  * Исправлено: не распознавались ссылки на асинхронные операции, если они
    использовали :code:`http://` (вместо :code:`https://`).
    Иногда Яндекс.Диск может вернуть :code:`http://` ссылку на асинхронную
    операцию. Теперь обе версии ссылок распознаются правильно, при этом,
    при получении информации об операции (через :code:`get_operation_status()`)
    всегда используется :code:`https://` версия ссылки, даже если Яндекс.Диск
    вернул :code:`http://`.

* **Release 1.3.2 (2021-07-10)**

  * Исправлено значение :code:`__version__`

* **Release 1.3.1 (2021-07-10)**

  * Исправлена ошибка :code:`AttributeError` в объекте :code:`SessionWithHeaders` (`PR #1`_)
  * Исправлены тесты корзины

* **Release 1.3.0 (2019-07-06)**

  * Реализована поддержка `async/await`
  * Библиотека была переименована из `yadisk`_ в `yadisk-async`

Следующие релизы относятся к оригинальной библиотеке `yadisk`_:

* **Release 1.2.14 (2019-03-26)**

  * Исправлена ошибка :code:`TypeError` в функциях :code:`get_public_*` при
    использовании с параметром :code:`path` (`issue #7`_)
  * Добавлен аттрибут :code:`unlimited_autoupload_enabled` для :code:`DiskInfoObject`

* **Release 1.2.13 (2019-02-23)**

  * Добавлен :code:`md5` параметр для :code:`remove()`
  * Добавлен :code:`UserPublicInfoObject`
  * Добавлен аттрибут :code:`country` для :code:`UserObject`
  * Добавлен аттрибут :code:`photoslice_time` для :code:`ResourceObject`, :code:`PublicResourceObject`
    и :code:`TrashResourceObject`

* **Release 1.2.12 (2018-10-11)**

  * Исправлен баг: не работает параметр `fields` в `listdir()` (`issue #4`_)

* **Release 1.2.11 (2018-06-30)**

  * Добавлен недостающий параметр :code:`sort` для :code:`get_meta()`
  * Добавлены аттрибуты :code:`file` и :code:`antivirus_status` для :code:`ResourceObject`,
    :code:`PublicResourceObject` и :code:`TrashResourceObject`
  * Добавлен параметр :code:`headers`
  * Исправлена опечатка в :code:`download()` и :code:`download_public()` (`issue #2`_)
  * Убран параметр :code:`*args`

* **Release 1.2.10 (2018-06-14)**

  * Исправлено поведение :code:`timeout=None`. :code:`None` должен означать „без таймаута“,
    но в предыдущих версиях значение :code:`None` было синонимично со стандартным таймаутом.

* **Release 1.2.9 (2018-04-28)**

  * Изменена лицензия на LGPLv3 (см. :code:`COPYING` и :code:`COPYING.lesser`)
  * Другие изменения информации о пакете

* **Release 1.2.8 (2018-04-17)**

  * Исправлено несколько опечаток: у :code:`PublicResourceListObject.items` и
    :code:`TrashResourceListObject.items` были неправильные типы данных
  * Псевдонимы полей в параметре :code:`fields` заменяются при выполнении
    запросов API (например, :code:`embedded` -> :code:`_embedded`)

* **Release 1.2.7 (2018-04-15)**

  * Исправлен баг перемотки файла при загрузке/скачивании после повторной попытки

* **Release 1.2.6 (2018-04-13)**

  * Теперь объекты сессий :code:`requests` кэшируются, чтобы их можно
    было переиспользовать (иногда может существенно ускорить выполнение запросов)
  * :code:`keep-alive` отключается при загрузке/скачивании файлов по умолчанию

* **Release 1.2.5 (2018-03-31)**

  * Исправлен баг (ошибка на единицу) в :code:`utils.auto_retry()` (иногда мог вызвать :code:`AttributeError`)
  * Повторные попытки применяются для :code:`upload()`, :code:`download()` и :code:`download_public()` целиком
  * Задано :code:`stream=True` для :code:`download()` и :code:`download_public()`
  * Другие мелкие исправления

* **Release 1.2.4 (2018-02-19)**

  * Исправлена опечатка (:code:`TokenObject.exprires_in` -> :code:`TokenObject.expires_in`)

* **Release 1.2.3 (2018-01-20)**

  * Исправлено :code:`TypeError` при вызове :code:`WrongResourceTypeError`

* **Release 1.2.2 (2018-01-19)**

  * :code:`refresh_token()` больше не требует валидный или пустой токен.

* **Release 1.2.1 (2018-01-14)**

  * Исправлена неработоспособность повторных попыток.

* **Release 1.2.0 (2018-01-14)**

  * Исправлено использование :code:`n_retries=0` в :code:`upload()`, :code:`download()` и :code:`download_public()`
  * :code:`upload()`, :code:`download()` и :code:`download_public()` больше не возвращают ничего (см. документацию)
  * Добавлен модуль :code:`utils` (см. документацию)
  * Добавлены :code:`RetriableYaDiskError`, :code:`WrongResourceTypeError`, :code:`BadGatewayError` и :code:`GatewayTimeoutError`
  * :code:`listdir()` теперь вызывает :code:`WrongResourceTypeError` вместо :code:`NotADirectoryError`

* **Release 1.1.1 (2017-12-29)**

  * Исправлена обработка аргументов в :code:`upload()`, :code:`download()` и :code:`download_public()`.
    До этого использование :code:`n_retries` и :code:`retry_interval` вызывало исключение (:code:`TypeError`).

* **Release 1.1.0 (2017-12-27)**

  * Усовершенствованные исключения (см. документацию)
  * Добавлена поддержка параметра :code:`force_async`
  * Мелкие исправления багов

* **Release 1.0.8 (2017-11-29)**

  * Исправлен ещё один баг в :code:`listdir()`

* **Release 1.0.7 (2017-11-04)**

  * Добавлен :code:`install_requires` в :code:`setup.py`

* **Release 1.0.6 (2017-11-04)**

  * Некоторые функции теперь возвращают :code:`OperationLinkObject`

* **Release 1.0.5 (2017-10-29)**

  * Исправлен :code:`setup.py`, теперь исключает тесты

* **Release 1.0.4 (2017-10-23)**

  * Исправлены баги в :code:`upload`, :code:`download` и :code:`listdir`
  * Значение по-умолчанию :code:`limit` в :code:`listdir` установлено в :code:`10000`

* **Release 1.0.3 (2017-10-22)**

  * Добавлен модуль :code:`settings`

* **Release 1.0.2 (2017-10-19)**

  * Исправлена функция :code:`get_code_url` (добавлены недостающие параметры)

* **Release 1.0.1 (2017-10-18)**

  * Исправлен серьёзный баг в :code:`GetTokenRequest` (добавлен недостающий параметр)

* **Release 1.0.0 (2017-10-18)**

  * Первый релиз

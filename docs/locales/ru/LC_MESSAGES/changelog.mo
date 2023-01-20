��    ;      �              �  c   �     1  *   N  u   y     �  /   	  $   9  h   ^  C   �  #        /  )   >  3   h      �  B   �  	      @   
  9   K  O   �  *   �  J      8   K  �   �  !   :	  �   \	  _   �	  ;   I
  {   �
  Z     m   \  I   �  @     B   U  �  �  b   \  �   �  '   i  :   �  O   �       !   2     T     d  B   t  z   �     2     D  $   _  L   �  .   �  :      (   ;  l   d  ?   �  )     O   ;  <   �  Y   �  �  "  o   �  '   \  ?   �  �   �  +   P  1   |  9   �  |   �  X   e  F   �  (     F   .  S   u  \   �  S   &  !   z  u   �  d     ]   w  3   �  g   	  q   q  )  �  I       W  �   c  M      �   Q   �   
!  �   �!  �   h"  |   �"  Z   w#  �  �#  �   x&  �   '  ^   �'  B   S(  p   �(  .   )  8   6)     o)  .   �)  7   �)  �   �)  0   �*  D   +  #   [+  ~   +  Y   �+  E   X,  _   �,  �   �,  n   �-  Y    .  d   z.  c   �.  �   C/   Added `RetriableYaDiskError`, `WrongResourceTypeError`, `BadGatewayError` and `GatewayTimeoutError` Added `UserPublicInfoObject` Added `country` attribute for `UserObject` Added `file` and `antivirus_status` attributes for `ResourceObject`, `PublicResourceObject` and `TrashResourceObject` Added `headers` parameter Added `install_requires` argument to `setup.py` Added `md5` parameter for `remove()` Added `photoslice_time` attribute for `ResourceObject`, `PublicResourceObject` and `TrashResourceObject` Added `unlimited_autoupload_enabled` attribute for `DiskInfoObject` Added `utils` module (see the docs) Added settings Added support for `force_async` parameter Added the missing parameter `sort` for `get_meta()` Better exceptions (see the docs) Changed the license to LGPLv3 (see `COPYING` and `COPYING.lesser`) Changelog Disable `keep-alive` when uploading/downloading files by default Fixed `AttributeError` in `SessionWithHeaders` (`PR #1`_) Fixed `TokenObject` having `exprires_in` instead of `expires_in` (fixed a typo) Fixed `__version__` having the wrong value Fixed `fields` parameter not working properly in `listdir()` (`issue #4`_) Fixed `get_code_url` function (added missing parameters) Fixed `issue #26`_: ':' character in filenames causes `BadRequestError`. This is due the behavior of Yandex.Disk's REST API itself but is avoided on the library level with this fix. Fixed `setup.py` to exclude tests Fixed `timeout=None` behavior. `None` is supposed to mean 'no timeout' but in the older versions it was synonymous with the default timeout. Fixed a `TypeError` in `get_public_*` functions when passing `path` parameter (see `issue #7`_) Fixed a `TypeError` when `WrongResourceTypeError` is raised Fixed a bug in `check_token()`: could throw `ForbiddenError` if the application lacks necessary permissions (`issue #23`_). Fixed a bug in `is_file()` and `is_dir()`: a typo was causing `AttributeError` (`PR #6`_). Fixed a couple of typos: `PublicResourceListObject.items` and `TrashResourceListObject.items` had wrong types Fixed a file rewinding bug when uploading/downloading files after a retry Fixed a major bug in `GetTokenRequest` (added missing parameter) Fixed a typo in `download()` and `download_public()` (`issue #2`_) Fixed an issue where `http://` links were not recognized as operation links (they were assumed to always be `https://`, since all the other requests are always HTTPS). Occasionally, Yandex.Disk can for some reason return an `http://` link to an asynchronous operation instead of `https://`. Both links are now recognized correctly and an `https://` version will always be used by `get_operation_status()`, regardless of which one Yandex.Disk returned. Fixed an off-by-one bug in `utils.auto_retry()` (which could sometimes result in `AttributeError`) Fixed argument handling in `upload()`, `download()` and `download_public()`. Previously, passing `n_retries` and `retry_interval` would raise an exception (`TypeError`). Fixed auto retries not working. Whoops. Fixed bugs in `upload`, `download` and `listdir` functions Fixed passing `n_retries=0` to `upload()`, `download()` and `download_public()` Fixed trash bin tests Fixed yet another `listdir()` bug Initial release Minor bug fixes Modified the original library (`yadisk`_) to support `async/await` Now caching `requests` sessions so that open connections can be reused (which can significantly speed things up sometimes) Other minor fixes Other package info updates Removed `*args` parameter everywhere Retry the whole request for `upload()`, `download()` and `download_public()` Return `OperationLinkObject` in some functions Set `stream=True` for `download()` and `download_public()` Set default `listdir` `limit` to `10000` Substitute field aliases in `fields` parameter when performing API requests (e.g. `embedded` -> `_embedded`) The following releases are for `yadisk`_, the original library: The library was renamed to `yadisk-async` `listdir()` now raises `WrongResourceTypeError` instead of `NotADirectoryError` `refresh_token()` no longer requires a valid or empty token. `upload()`, `download()` and `download_public()` no longer return anything (see the docs) Project-Id-Version: YaDisk 1.3.6
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2023-01-20 20:15+0500
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language: ru
Language-Team: ru <LL@li.org>
Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 8bit
Generated-By: Babel 2.11.0
 Добавлены `RetriableYaDiskError`, `WrongResourceTypeError`, `BadGatewayError` и `GatewayTimeoutError` Добавлен `UserPublicInfoObject` Добавлен аттрибут `country` для `UserObject` Добавлены аттрибуты `file` и `antivirus_status` для `ResourceObject`, `PublicResourceObject` и `TrashResourceObject` Добавлен параметр `headers` Добавлен `install_requires` в `setup.py` Добавлен параметр `md5` для `remove()` Добавлен аттрибут `photoslice_time` для `ResourceObject`, `PublicResourceObject` и `TrashResourceObject` Добавлен аттрибут `unlimited_autoupload_enabled` для `DiskInfoObject` Добавлен модуль `utils` (см. документацию) Добавлен модуль `settings` Добавлена поддержка параметра `force_async` Добавлен недостающий параметр `sort` для `get_meta()` Усовершенствованные исключения (см. документацию) Изменена лицензия на LGPLv3 (см. `COPYING` и `COPYING.lesser`) История изменений `keep-alive` отключается при загрузке/скачивании файлов по умолчанию Исправлена ошибка `AttributeError` в объекте `SessionWithHeaders` (`PR #1`_) Исправлена опечатка (`TokenObject.exprires_in` -> `TokenObject.expires_in`) Исправлено значение `__version__` Исправлен баг: не работает параметр `fields` в `listdir()` (`issue #4`_) Исправлена функция `get_code_url` (добавлены недостающие параметры) Исправлено `issue #26`_: символ ':' в именах файлов приводит к `BadRequestError`. Это поведение вызвано работой самого REST API Яндекс.Диска, но было исправлено на уровне библиотеки. Исправлен `setup.py`, теперь исключает тесты Исправлено поведение `timeout=None`. `None` должен означать 'без таймаута', но в предыдущих версиях значение `None` было синонимично со стандартным таймаутом. Исправлена ошибка `TypeError` в функциях `get_public_*` при использовании с параметром `path` (`issue #7`_) Исправлено `TypeError` при вызове `WrongResourceTypeError` Исправлен баг в `check_token()`: функция могла вызвать `ForbiddenError`,если у приложения недостатчно прав (`issue #23`_). Исправлен баг в `is_file()` и `is_dir()`: из-за опечатки функции вызывали исключение `AttributeError` (`PR #6`_). Исправлено несколько опечаток: у `PublicResourceListObject.items` и `TrashResourceListObject.items` были неправильные типы данных Исправлен баг перемотки файла при загрузке/скачивании после повторной попытки Исправлен серьёзный баг в `GetTokenRequest` (добавлен недостающий параметр) Исправлена опечатка в `download()` и `download_public()` (`issue #2`_) Исправлено: не распознавались ссылки на асинхронные операции, если они использовали `http://` (вместо `https://`). Иногда Яндекс.Диск может вернуть `http://` ссылку на асинхронную операцию. Теперь обе версии ссылок распознаются правильно, при этом, при получении информации об операции (через `get_operation_status()`) всегда используется `https://` версия ссылки, даже если Яндекс.Диск вернул `http://`. Исправлен баг (ошибка на единицу) в `utils.auto_retry()` (иногда мог вызвать `AttributeError`) Исправлена обработка аргументов в `upload()`, `download()` и `download_public()`. До этого использование `n_retries` и `retry_interval` вызывало исключение (`TypeError`). Исправлена неработоспособность повторных попыток. Исправлены баги в `upload`, `download` и `listdir` Исправлено использование `n_retries=0` в `upload()`, `download()` и `download_public()` Исправлены тесты корзины Исправлен ещё один баг в `listdir()` Первый релиз Мелкие исправления багов Реализована поддержка `async/await` Теперь объекты сессий `requests` кэшируются, чтобы их можно было переиспользовать (иногда может существенно ускорить выполнение запросов) Другие мелкие исправления Другие изменения информации о пакете Убран параметр `*args` Повторные попытки применяются для `upload()`, `download()` и `download_public()` целиком Некоторые функции теперь возвращают `OperationLinkObject` Задано `stream=True` для `download()` и `download_public()` Значение по-умолчанию `limit` в `listdir` установлено в `10000` Псевдонимы полей в параметре `fields` заменяются при выполнении запросов API (например, `embedded` -> `_embedded`) Следующие релизы относятся к оригинальной библиотеке `yadisk`_: Библиотека была переименована из `yadisk`_ в `yadisk-async` `listdir()` теперь вызывает `WrongResourceTypeError` вместо `NotADirectoryError` `refresh_token()` больше не требует валидный или пустой токен. `upload()`, `download()` и `download_public()` больше не возвращают ничего (см. документацию) 
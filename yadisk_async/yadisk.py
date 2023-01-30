# -*- coding: utf-8 -*-

import asyncio
import inspect
import threading
from pathlib import PurePosixPath

from urllib.parse import urlencode
import io
from .common import FileOrPath, FileOrPathDestination

from . import settings
from .session import SessionWithHeaders
from .api import *
from .exceptions import (
    InvalidResponseError, UnauthorizedError, OperationNotFoundError,
    PathNotFoundError, WrongResourceTypeError)
from .utils import get_exception, auto_retry
from .objects import ResourceLinkObject, PublicResourceLinkObject

from typing import Any, Optional, Union, IO, TYPE_CHECKING
from .compat import Callable, AsyncGenerator, List, Awaitable, Dict

import aiofiles

if TYPE_CHECKING:
    from .objects import (
        TokenObject, TokenRevokeStatusObject, DiskInfoObject,
        ResourceObject, OperationLinkObject,
        TrashResourceObject, PublicResourceObject,
        PublicResourcesListObject)

__all__ = ["YaDisk"]

async def _exists(get_meta_function: Callable[..., Awaitable], /, *args, **kwargs) -> bool:
    kwargs["limit"] = 0

    try:
        await get_meta_function(*args, **kwargs)

        return True
    except PathNotFoundError:
        return False

ResourceType = Union["ResourceObject", "PublicResourceObject", "TrashResourceObject"]

async def _get_type(get_meta_function: Callable[..., Awaitable[ResourceType]],
                    /, *args, **kwargs) -> str:
    kwargs["limit"] = 0
    kwargs["fields"] = ["type"]

    type = (await get_meta_function(*args, **kwargs)).type

    if type is None:
        raise InvalidResponseError("Response did not contain the type field")

    return type

async def _listdir(get_meta_function: Callable[..., Awaitable[ResourceType]],
                   path: str, /, **kwargs) -> AsyncGenerator:
    kwargs.setdefault("limit", 10000)

    if kwargs.get("fields") is None:
        kwargs["fields"] = []

    kwargs["fields"] = ["embedded.items.%s" % (k,) for k in kwargs["fields"]]

    # Fields that are absolutely necessary
    NECESSARY_FIELDS = ["type",
                        "embedded",
                        "embedded.offset",
                        "embedded.limit",
                        "embedded.total",
                        "embedded.items"]

    kwargs["fields"].extend(NECESSARY_FIELDS)

    result = await get_meta_function(path, **kwargs)

    if result.type == "file":
        raise WrongResourceTypeError("%r is a file" % (path,))

    if result.embedded is None:
        raise InvalidResponseError("Response did not contain _embedded field")

    if (result.type is None or result.embedded.items is None or
        result.embedded.offset is None or result.embedded.limit is None or
        result.embedded.total is None):
        raise InvalidResponseError("Response did not contain key field")

    for child in result.embedded.items:
        yield child

    limit: int = result.embedded.limit
    offset: int = result.embedded.offset
    total: int = result.embedded.total

    while offset + limit < total:
        offset += limit
        kwargs["offset"] = offset
        result = await get_meta_function(path, **kwargs)

        if result.embedded is None:
            raise InvalidResponseError("Response did not contain _embedded field")

        if (result.type is None or result.embedded.items is None or
            result.embedded.offset is None or result.embedded.limit is None or
            result.embedded.total is None):
            raise InvalidResponseError("Response did not contain key field")

        for child in result.embedded.items:
            yield child

        limit: int = result.embedded.limit
        total: int = result.embedded.total

class UnclosableFile(io.IOBase):
    """
        File-like object that cannot be closed.
        It exists only to prevent aiohttp from closing the file after uploading
        it with the PUT request.
    """

    def __init__(self, file: IO):
        io.IOBase.__init__(self)
        self.file = file

    def close(self) -> None:
        pass

    @property
    def closed(self) -> bool:
        return self.file.closed

    def flush(self) -> None:
        self.file.flush()

    def seek(self, *args, **kwargs) -> int:
        return self.file.seek(*args, **kwargs)

    def seekable(self) -> bool:
        return self.file.seekable()

    def tell(self) -> int:
        return self.file.tell()

    def truncate(self, *args, **kwargs) -> int:
        return self.file.truncate(*args, **kwargs)

    def writable(self) -> bool:
        return self.file.writable()

    def readable(self) -> bool:
        return self.file.readable()

    def read(self, *args, **kwargs) -> Union[str, bytes]:
        return self.file.read(*args, **kwargs)

    def readline(self, *args, **kwargs) -> Union[str, bytes]:
        return self.file.readline(*args, **kwargs)

    def readlines(self, *args, **kwargs) -> List[Union[str, bytes]]:
        return self.file.readlines(*args, **kwargs)

    def write(self, *args, **kwargs) -> int:
        return self.file.write(*args, **kwargs)

    def writelines(self, *args, **kwargs) -> None:
        return self.file.writelines(*args, **kwargs)

async def read_in_chunks(file: IO, chunk_size: int = 64 * 1024) -> Union[AsyncGenerator[str, None],
                                                                         AsyncGenerator[bytes, None]]:
    while chunk := await file.read(chunk_size):
        yield chunk

def is_async_func(func: Any) -> bool:
    return inspect.isgeneratorfunction(func) or asyncio.iscoroutinefunction(func)

def is_async_file(file: Any) -> bool:
    read_method = getattr(file, "read", None)

    return is_async_func(read_method)

def _apply_default_args(args: Dict[str, Any], default_args: Dict[str, Any]) -> None:
    new_args = dict(default_args)
    new_args.update(args)
    args.clear()
    args.update(new_args)

class YaDisk:
    """
        Implements access to Yandex.Disk REST API.

        .. note::
           Do not forget to call :any:`YaDisk.close` or use the `async with` statement
           to close all the connections. Otherwise, you may get a warning.

           In the original library this is handled in the destructor, but since
           :any:`aiohttp.ClientSession.close` is a coroutine function the
           same cannot be done here, so you have to do it explicitly.

        :param id: application ID
        :param secret: application secret password
        :param token: application token
        :param default_args: `dict` or `None`, default arguments for methods.
                             Can be used to set the default timeout, headers, etc.

        :ivar id: `str`, application ID
        :ivar secret: `str`, application secret password
        :ivar token: `str`, application token
        :ivar default_args: `dict`, default arguments for methods. Can be used to
                            set the default timeout, headers, etc.

        The following exceptions may be raised by most API requests:

        :raises BadRequestError: server returned HTTP code 400
        :raises FieldValidationError: request contains fields with invalid data
        :raises UnauthorizedError: server returned HTTP code 401
        :raises ForbiddenError: server returned HTTP code 403
        :raises NotAcceptableError: server returned HTTP code 406
        :raises ConflictError: server returned HTTP code 409
        :raises PayloadTooLargeError: server returned code 413
        :raises UnsupportedMediaError: server returned HTTP code 415
        :raises LockedError: server returned HTTP code 423
        :raises TooManyRequestsError: server returned HTTP code 429
        :raises InternalServerError: server returned HTTP code 500
        :raises BadGatewayError: server returned HTTP code 502
        :raises UnavailableError: server returned HTTP code 503
        :raises GatewayTimeoutError: server returned HTTP code 504
        :raises InsufficientStorageError: server returned HTTP code 509
        :raises UnknownYaDiskError: other unknown error
    """

    id: str
    secret: str
    token: str
    default_args: Dict[str, Any]

    def __init__(self,
                 id: str ="",
                 secret: str = "",
                 token: str = "",
                 default_args: Optional[Dict[str, Any]] = None):
        self.id = id
        self.secret = secret
        self.token = token
        self.default_args = {} if default_args is None else default_args

        self._sessions = {}

    def _get_session(self, token, tid):
        try:
            return self._sessions[(token, tid)]
        except KeyError:
            session = self.make_session(token)
            self._sessions[(token, tid)] = session

            return session

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs) -> None:
        await self.close()

    async def close(self) -> None:
        """
            Closes all sessions and clears the session cache.
            Do not call this method while there are other active threads using this object.

            This method can also be called implicitly by using the `async with`
            statement.
        """

        for session in self._sessions.values():
            await session.close()

        self.clear_session_cache()

    def clear_session_cache(self) -> None:
        """
            Clears the session cache. Unused sessions will NOT be closed.
        """

        self._sessions.clear()

    def make_session(self, token: Optional[str] = None) -> SessionWithHeaders:
        """
            Prepares :any:`aiohttp.ClientSession` object with headers needed for API.

            :param token: application token, equivalent to `self.token` if `None`
            :returns: `aiohttp.ClientSession`
        """

        if token is None:
            token = self.token

        session = SessionWithHeaders()

        if token:
            session.headers["Authorization"] = "OAuth " + token

        return session

    def get_session(self, token: Optional[str] = None) -> SessionWithHeaders:
        """
            Like :any:`YaDisk.make_session` but cached.

            :returns: :any:`aiohttp.ClientSession`, different instances for different threads
        """

        if token is None:
            token = self.token

        return self._get_session(token, threading.get_ident())

    def get_auth_url(self, **kwargs) -> str:
        """
            Get authentication URL for the user to go to.

            :param type: response type ("code" to get the confirmation code or "token" to get the token automatically)
            :param device_id: unique device ID, must be between 6 and 50 characters
            :param device_name: device name, should not be longer than 100 characters
            :param display: indicates whether to use lightweight layout, values other than "popup" are ignored
            :param login_hint: username or email for the account the token is being requested for
            :param scope: list of permissions for the application
            :param optional_scope: list of optional permissions for the application
            :param force_confirm: if True, user will be required to confirm access to the account
                                  even if the user has already granted access for the application
            :param state: The state string, which Yandex.OAuth returns without any changes (<= 1024 characters)

            :returns: authentication URL
        """

        type           = kwargs.get("type")
        device_id      = kwargs.get("device_id")
        device_name    = kwargs.get("device_name")
        display        = kwargs.get("display", "popup")
        login_hint     = kwargs.get("login_hint")
        scope          = kwargs.get("scope")
        optional_scope = kwargs.get("optional_scope")
        force_confirm  = kwargs.get("force_confirm", True)
        state          = kwargs.get("state")

        if type not in {"code", "token"}:
            raise ValueError("type must be either 'code' or 'token'")

        params = {"response_type": type,
                  "client_id":     self.id,
                  "display":       display,
                  "force_confirm": "yes" if force_confirm else "no"}

        if device_id is not None:
            params["device_id"] = device_id

        if device_name is not None:
            params["device_name"] = device_name

        if login_hint is not None:
            params["login_hint"] = login_hint

        if scope is not None:
            params["scope"] = " ".join(scope)

        if optional_scope is not None:
            params["optional_scope"] = " ".join(optional_scope)

        if state is not None:
            params["state"] = state

        return "https://oauth.yandex.ru/authorize?" + urlencode(params)

    def get_code_url(self, **kwargs) -> str:
        """
            Get the URL for the user to get the confirmation code.
            The confirmation code can later be used to get the token.

            :param device_id: unique device ID, must be between 6 and 50 characters
            :param device_name: device name, should not be longer than 100 characters
            :param display: indicates whether to use lightweight layout, values other than "popup" are ignored
            :param login_hint: username or email for the account the token is being requested for
            :param scope: list of permissions for the application
            :param optional_scope: list of optional permissions for the application
            :param force_confirm: if True, user will be required to confirm access to the account
                                  even if the user has already granted access for the application
            :param state: The state string, which Yandex.OAuth returns without any changes (<= 1024 characters)

            :returns: authentication URL
        """

        kwargs["type"] = "code"

        return self.get_auth_url(**kwargs)

    async def get_token(self, code: str, /, **kwargs) -> "TokenObject":
        """
            Get a new token.

            :param code: confirmation code
            :param device_id: unique device ID (between 6 and 50 characters)
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises BadRequestError: invalid or expired code, application ID or secret

            :returns: :any:`TokenObject`
        """

        _apply_default_args(kwargs, self.default_args)

        async with SessionWithHeaders() as session:
            request = GetTokenRequest(session, code, self.id, self.secret, **kwargs)
            await request.send()

            return await request.process()

    async def refresh_token(self, refresh_token: str, /, **kwargs) -> "TokenObject":
        """
            Refresh an existing token.

            :param refresh_token: the refresh token that was received with the token
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises BadRequestError: invalid or expired refresh token, application ID or secret

            :returns: :any:`TokenObject`
        """

        _apply_default_args(kwargs, self.default_args)

        async with SessionWithHeaders() as session:
            request = RefreshTokenRequest(
                session, refresh_token, self.id, self.secret, **kwargs)
            await request.send()

            return await request.process()

    async def revoke_token(self, token: Optional[str] = None, /, **kwargs) -> "TokenRevokeStatusObject":
        """
            Revoke the token.

            :param token: token to revoke, equivalent to `self.token` if `None`
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises BadRequestError: token cannot be revoked (not bound to this application, etc.)

            :returns: :any:`TokenRevokeStatusObject`
        """

        _apply_default_args(kwargs, self.default_args)

        if token is None:
            token = self.token

        async with SessionWithHeaders() as session:
            request = RevokeTokenRequest(
                session, token, self.id, self.secret, **kwargs)
            await request.send()

            return await request.process()

    async def get_disk_info(self, **kwargs) -> "DiskInfoObject":
        """
            Get disk information.

            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: :any:`DiskInfoObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = DiskInfoRequest(self.get_session(), **kwargs)
        await request.send()

        return await request.process()

    async def get_meta(self, path: str, /, **kwargs) -> "ResourceObject":
        """
            Get meta information about a file/directory.

            :param path: path to the resource
            :param limit: number of children resources to be included in the response
            :param offset: number of children resources to be skipped in the response
            :param preview_size: size of the file preview
            :param preview_crop: `bool`, cut the preview to the size specified in the `preview_size`
            :param sort: `str`, field to be used as a key to sort children resources
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: :any:`ResourceObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = GetMetaRequest(self.get_session(), path, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def exists(self, path: str, /, **kwargs) -> bool:
        """
            Check whether `path` exists.

            :param path: path to the resource
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: `bool`
        """

        _apply_default_args(kwargs, self.default_args)

        return await _exists(self.get_meta, path, **kwargs)

    async def get_type(self, path: str, /, **kwargs) -> str:
        """
            Get resource type.

            :param path: path to the resource
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: "file" or "dir"
        """

        _apply_default_args(kwargs, self.default_args)

        return await _get_type(self.get_meta, path, **kwargs)

    async def is_file(self, path: str, /, **kwargs) -> bool:
        """
            Check whether `path` is a file.

            :param path: path to the resource
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: `True` if `path` is a file, `False` otherwise (even if it doesn't exist)
        """

        _apply_default_args(kwargs, self.default_args)

        try:
            return (await self.get_type(path, **kwargs)) == "file"
        except PathNotFoundError:
            return False

    async def is_dir(self, path: str, /, **kwargs) -> bool:
        """
            Check whether `path` is a directory.

            :param path: path to the resource
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: `True` if `path` is a directory, `False` otherwise (even if it doesn't exist)
        """

        _apply_default_args(kwargs, self.default_args)

        try:
            return (await self.get_type(path, **kwargs)) == "dir"
        except PathNotFoundError:
            return False

    async def listdir(self, path: str, /, **kwargs) -> AsyncGenerator["ResourceObject", None]:
        """
            Get contents of `path`.

            :param path: path to the directory
            :param limit: number of children resources to be included in the response
            :param offset: number of children resources to be skipped in the response
            :param preview_size: size of the file preview
            :param preview_crop: `bool`, cut the preview to the size specified in the `preview_size`
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises WrongResourceTypeError: resource is not a directory

            :returns: generator of :any:`ResourceObject`
        """

        _apply_default_args(kwargs, self.default_args)

        return _listdir(self.get_meta, path, **kwargs)

    async def get_upload_link(self, path: str, /, **kwargs) -> str:
        """
            Get a link to upload the file using the PUT request.

            :param path: destination path
            :param overwrite: `bool`, determines whether to overwrite the destination
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ParentNotFoundError: parent directory doesn't exist
            :raises PathExistsError: destination path already exists
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request
            :raises InsufficientStorageError: cannot upload file due to lack of storage space
            :raises UploadTrafficLimitExceededError: upload limit has been exceeded

            :returns: `str`
        """

        _apply_default_args(kwargs, self.default_args)

        request = GetUploadLinkRequest(self.get_session(), path, **kwargs)
        await request.send()

        return (await request.process(yadisk=self)).href

    async def _upload(self,
                      get_upload_link_function: Callable[..., Awaitable[str]],
                      file_or_path: FileOrPath,
                      dst_path: str, /, **kwargs) -> None:
        try:
            timeout = kwargs["timeout"]
        except KeyError:
            timeout = settings.DEFAULT_UPLOAD_TIMEOUT

        retry_interval = kwargs.get("retry_interval")

        if retry_interval is None:
            retry_interval = settings.DEFAULT_UPLOAD_RETRY_INTERVAL

        n_retries = kwargs.get("n_retries")

        if n_retries is None:
            n_retries = settings.DEFAULT_N_RETRIES

        kwargs["timeout"] = timeout

        file = None
        close_file = False
        generator_factory: Optional[Callable[[], AsyncGenerator]] = None

        session = self.get_session()

        try:
            if isinstance(file_or_path, (str, bytes)):
                close_file = True
                file = await aiofiles.open(file_or_path, "rb")
            elif inspect.isasyncgenfunction(file_or_path):
                generator_factory = file_or_path
            else:
                close_file = False
                file = file_or_path

            if generator_factory is None:
                if is_async_func(file.tell):
                    file_position = await file.tell()
                else:
                    file_position = file.tell()

            async def attempt():
                temp_kwargs = dict(kwargs)
                temp_kwargs["n_retries"] = 0
                temp_kwargs["retry_interval"] = 0.0

                link = await get_upload_link_function(dst_path, **temp_kwargs)

                # session.put() doesn't accept these parameters
                for k in ("n_retries", "retry_interval", "overwrite", "fields"):
                    temp_kwargs.pop(k, None)

                # Disable keep-alive by default, since the upload server is random
                try:
                    temp_kwargs["headers"].setdefault("Connection", "close")
                except KeyError:
                    temp_kwargs["headers"] = {"Connection": "close"}

                data = None

                if generator_factory is None:
                    if is_async_func(file.seek):
                        await file.seek(file_position)
                    else:
                        file.seek(file_position)

                    if is_async_func(file.read):
                        data = read_in_chunks(file)
                    else:
                        # UnclosableFile is used here to prevent aiohttp from closing the file
                        # after uploading it
                        data = UnclosableFile(file)
                else:
                    data = generator_factory()

                async with session.put(link, data=data, **temp_kwargs) as response:
                    if response.status != 201:
                        raise await get_exception(response)

            await auto_retry(attempt, n_retries, retry_interval)
        finally:
            if close_file and file is not None:
                await file.close()

    async def upload(self,
                     path_or_file: FileOrPath,
                     dst_path: str, /, **kwargs) -> ResourceLinkObject:
        """
            Upload a file to disk.

            :param path_or_file: path, file-like object or an async generator function to be uploaded
            :param dst_path: destination path
            :param overwrite: if `True`, the resource will be overwritten if it already exists,
                              an error will be raised otherwise
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ParentNotFoundError: parent directory doesn't exist
            :raises PathExistsError: destination path already exists
            :raises InsufficientStorageError: cannot upload file due to lack of storage space
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request
            :raises UploadTrafficLimitExceededError: upload limit has been exceeded

            :returns: :any:`ResourceLinkObject`, link to the destination resource
        """

        _apply_default_args(kwargs, self.default_args)

        await self._upload(self.get_upload_link, path_or_file, dst_path, **kwargs)
        return ResourceLinkObject.from_path(dst_path, yadisk=self)

    async def upload_by_link(self,
                             file_or_path: FileOrPath,
                             link: str, /, **kwargs) -> None:
        """
            Upload a file to disk using an upload link.

            :param file_or_path: path, file-like object or an async generator function to be uploaded
            :param link: upload link
            :param overwrite: if `True`, the resource will be overwritten if it already exists,
                              an error will be raised otherwise
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises InsufficientStorageError: cannot upload file due to lack of storage space
        """

        _apply_default_args(kwargs, self.default_args)

        async def get_link(*args, **kwargs) -> str:
            return link

        await self._upload(get_link, file_or_path, "", **kwargs)

    async def get_download_link(self, path: str, /, **kwargs) -> str:
        """
            Get a download link for a file (or a directory).

            :param path: path to the resource
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: `str`
        """

        _apply_default_args(kwargs, self.default_args)

        request = GetDownloadLinkRequest(self.get_session(), path, **kwargs)
        await request.send()

        return (await request.process(yadisk=self)).href

    async def _download(self,
                        get_download_link_function: Callable[..., Awaitable[str]],
                        src_path: str,
                        file_or_path: FileOrPathDestination, /, **kwargs) -> None:
        n_retries = kwargs.get("n_retries")

        if n_retries is None:
            n_retries = settings.DEFAULT_N_RETRIES

        retry_interval = kwargs.get("retry_interval")

        if retry_interval is None:
            retry_interval = settings.DEFAULT_RETRY_INTERVAL

        try:
            timeout = kwargs["timeout"]
        except KeyError:
            timeout = settings.DEFAULT_TIMEOUT

        kwargs["timeout"] = timeout

        file = None
        close_file = False

        session = self.get_session()

        try:
            if isinstance(file_or_path, (str, bytes)):
                close_file = True
                file = await aiofiles.open(file_or_path, "wb")
            else:
                close_file = False
                file = file_or_path

            if is_async_func(file.tell):
                file_position = await file.tell()
            else:
                file_position = file.tell()

            async def attempt() -> None:
                temp_kwargs = dict(kwargs)
                temp_kwargs["n_retries"] = 0
                temp_kwargs["retry_interval"] = 0.0
                link = await get_download_link_function(src_path, **temp_kwargs)

                # session.get() doesn't accept these parameters
                for k in ("n_retries", "retry_interval", "fields"):
                    temp_kwargs.pop(k, None)

                # Disable keep-alive by default, since the download server is random
                try:
                    temp_kwargs["headers"].setdefault("Connection", "close")
                except KeyError:
                    temp_kwargs["headers"] = {"Connection": "close"}

                if is_async_func(file.seek):
                    await file.seek(file_position)
                else:
                    file.seek(file_position)

                async with session.get(link, **temp_kwargs) as response:
                    async for chunk in response.content.iter_chunked(8192):
                        if is_async_func(file.write):
                            await file.write(chunk)
                        else:
                            file.write(chunk)

                    if response.status != 200:
                        raise await get_exception(response)

            return await auto_retry(attempt, n_retries, retry_interval)
        finally:
            if close_file and file is not None:
                await file.close()

    async def download(self,
                       src_path: str,
                       path_or_file: FileOrPathDestination, /, **kwargs) -> ResourceLinkObject:
        """
            Download the file.

            :param src_path: source path
            :param path_or_file: destination path or file-like object
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: :any:`ResourceLinkObject`, link to the source resource
        """

        _apply_default_args(kwargs, self.default_args)

        await self._download(self.get_download_link, src_path, path_or_file, **kwargs)
        return ResourceLinkObject.from_path(src_path, yadisk=self)

    async def download_by_link(self,
                               link: str,
                               file_or_path: FileOrPathDestination, /, **kwargs) -> None:
        """
            Download the file from the link.

            :param link: download link
            :param file_or_path: destination path or file-like object
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds
        """

        _apply_default_args(kwargs, self.default_args)

        async def get_link(*args, **kwargs) -> str:
            return link

        await self._download(get_link, "", file_or_path, **kwargs)

    async def remove(self, path: str, /, **kwargs) -> Optional["OperationLinkObject"]:
        """
            Remove the resource.

            :param path: path to the resource to be removed
            :param permanently: if `True`, the resource will be removed permanently,
                                otherwise, it will be just moved to the trash
            :param md5: `str`, MD5 hash of the file to remove
            :param force_async: forces the operation to be executed asynchronously
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises BadRequestError: MD5 check is only available for files
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: :any:`OperationLinkObject` if the operation is performed asynchronously, `None` otherwise
        """

        _apply_default_args(kwargs, self.default_args)

        request = DeleteRequest(self.get_session(), path, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def mkdir(self, path: str, /, **kwargs) -> ResourceLinkObject:
        """
            Create a new directory.

            :param path: path to the directory to be created
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ParentNotFoundError: parent directory doesn't exist
            :raises DirectoryExistsError: destination path already exists
            :raises InsufficientStorageError: cannot create directory due to lack of storage space
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: :any:`ResourceLinkObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = MkdirRequest(self.get_session(), path, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def check_token(self, token: Optional[str] = None, /, **kwargs) -> bool:
        """
            Check whether the token is valid.

            :param token: token to check, equivalent to `self.token` if `None`
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :returns: `bool`
        """

        _apply_default_args(kwargs, self.default_args)

        # Any ID will do, doesn't matter whether it exists or not
        fake_operation_id = "0000"

        try:
            # get_operation_status() doesn't require any permissions, unlike most other requests
            await self._get_operation_status(self.get_session(token), fake_operation_id, **kwargs)
            return True
        except UnauthorizedError:
            return False
        except OperationNotFoundError:
            return True

    async def get_trash_meta(self, path: str, /, **kwargs) -> "TrashResourceObject":
        """
            Get meta information about a trash resource.

            :param path: path to the trash resource
            :param limit: number of children resources to be included in the response
            :param offset: number of children resources to be skipped in the response
            :param preview_size: size of the file preview
            :param preview_crop: `bool`, cut the preview to the size specified in the `preview_size`
            :param sort: `str`, field to be used as a key to sort children resources
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: :any:`TrashResourceObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = GetTrashRequest(self.get_session(), path, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def trash_exists(self, path: str, /, **kwargs) -> bool:
        """
            Check whether the trash resource at `path` exists.

            :param path: path to the trash resource
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: `bool`
        """

        _apply_default_args(kwargs, self.default_args)

        return await _exists(self.get_trash_meta, path, **kwargs)

    async def copy(self,
                   src_path: str,
                   dst_path: str, /, **kwargs) -> Union[ResourceLinkObject, "OperationLinkObject"]:
        """
            Copy `src_path` to `dst_path`.
            If the operation is performed asynchronously, returns the link to the operation,
            otherwise, returns the link to the newly created resource.

            :param src_path: source path
            :param dst_path: destination path
            :param overwrite: if `True` the destination path can be overwritten,
                              otherwise, an error will be raised
            :param force_async: forces the operation to be executed asynchronously
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises PathExistsError: destination path already exists
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises InsufficientStorageError: cannot complete request due to lack of storage space
            :raises ResourceIsLockedError: resource is locked by another request
            :raises UploadTrafficLimitExceededError: upload limit has been exceeded

            :returns: :any:`ResourceLinkObject` or :any:`OperationLinkObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = CopyRequest(self.get_session(), src_path, dst_path, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def restore_trash(self,
                            path: str,
                            dst_path: Optional[str] = None, /, **kwargs) -> Union[ResourceLinkObject, "OperationLinkObject"]:
        """
            Restore a trash resource.
            Returns a link to the newly created resource or a link to the asynchronous operation.

            :param path: path to the trash resource to restore
            :param dst_path: destination path
            :param overwrite: `bool`, determines whether the destination can be overwritten
            :param force_async: forces the operation to be executed asynchronously
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises PathExistsError: destination path already exists
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: :any:`ResourceLinkObject` or :any:`OperationLinkObject`
        """

        _apply_default_args(kwargs, self.default_args)

        kwargs["dst_path"] = dst_path

        request = RestoreTrashRequest(self.get_session(), path, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def move(self,
                   src_path: str,
                   dst_path: str, /, **kwargs) -> Union["OperationLinkObject", ResourceLinkObject]:
        """
            Move `src_path` to `dst_path`.

            :param src_path: source path to be moved
            :param dst_path: destination path
            :param overwrite: `bool`, determines whether to overwrite the destination
            :param force_async: forces the operation to be executed asynchronously
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises PathExistsError: destination path already exists
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: :any:`ResourceLinkObject` or :any:`OperationLinkObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = MoveRequest(self.get_session(), src_path, dst_path, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def rename(self,
                     src_path: str,
                     new_name: str, /, **kwargs) -> Union[ResourceLinkObject, "OperationLinkObject"]:
        """
            Rename `src_path` to have filename `new_name`.
            Does the same as `move()` but changes only the filename.

            :param src_path: source path to be moved
            :param new_name: target filename to rename to
            :param overwrite: `bool`, determines whether to overwrite the destination
            :param force_async: forces the operation to be executed asynchronously
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises PathExistsError: destination path already exists
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request
            :raises ValueError: `new_name` is not a valid filename

            :returns: :any:`ResourceLinkObject` or :any:`OperationLinkObject`
        """

        _apply_default_args(kwargs, self.default_args)

        new_name = new_name.rstrip("/")

        if "/" in new_name or new_name in (".", ".."):
            raise ValueError(f"Invalid filename: {new_name}")

        dst_path = str(PurePosixPath(src_path).parent / new_name)

        return await self.move(src_path, dst_path, **kwargs)

    async def remove_trash(self, path: str, /, **kwargs) -> Optional["OperationLinkObject"]:
        """
            Remove a trash resource.

            :param path: path to the trash resource to be deleted
            :param force_async: forces the operation to be executed asynchronously
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: :any:`OperationLinkObject` if the operation is performed asynchronously, `None` otherwise
        """

        _apply_default_args(kwargs, self.default_args)

        request = DeleteTrashRequest(self.get_session(), path, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def publish(self, path: str, /, **kwargs) -> ResourceLinkObject:
        """
            Make a resource public.

            :param path: path to the resource to be published
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: :any:`ResourceLinkObject`, link to the resource
        """

        _apply_default_args(kwargs, self.default_args)

        request = PublishRequest(self.get_session(), path, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def unpublish(self, path: str, /, **kwargs) -> ResourceLinkObject:
        """
            Make a public resource private.

            :param path: path to the resource to be unpublished
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: :any:`ResourceLinkObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = UnpublishRequest(self.get_session(), path, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def save_to_disk(self, public_key: str, /, **kwargs) -> Union[ResourceLinkObject, "OperationLinkObject"]:
        """
            Saves a public resource to the disk.
            Returns the link to the operation if it's performed asynchronously,
            or a link to the resource otherwise.

            :param public_key: public key or public URL of the resource
            :param name: filename of the saved resource
            :param path: path to the copied resource in the public folder
            :param save_path: path to the destination directory (downloads directory by default)
            :param force_async: forces the operation to be executed asynchronously
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request
            :raises InsufficientStorageError: cannot upload file due to lack of storage space
            :raises UploadTrafficLimitExceededError: upload limit has been exceeded

            :returns: :any:`ResourceLinkObject` or :any:`OperationLinkObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = SaveToDiskRequest(self.get_session(), public_key, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def get_public_meta(self, public_key: str, /, **kwargs) -> "PublicResourceObject":
        """
            Get meta-information about a public resource.

            :param public_key: public key or public URL of the resource
            :param path: relative path to a resource in a public folder.
                         By specifying the key of the published folder in `public_key`,
                         you can request metainformation for any resource in the folder.
            :param offset: offset from the beginning of the list of nested resources
            :param limit: maximum number of nested elements to be included in the list
            :param sort: `str`, field to be used as a key to sort children resources
            :param preview_size: file preview size
            :param preview_crop: `bool`, allow preview crop
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: :any:`PublicResourceObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = GetPublicMetaRequest(self.get_session(), public_key, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def public_exists(self, public_key: str, /, **kwargs) -> bool:
        """
            Check whether the public resource exists.

            :param public_key: public key or public URL of the resource
            :param path: relative path to the resource within the public folder
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: `bool`
        """

        _apply_default_args(kwargs, self.default_args)

        return await _exists(self.get_public_meta, public_key, **kwargs)

    async def public_listdir(self, public_key: str, /, **kwargs) -> AsyncGenerator["PublicResourceObject", None]:
        """
            Get contents of a public directory.

            :param public_key: public key or public URL of the resource
            :param path: relative path to the resource in the public folder.
                         By specifying the key of the published folder in `public_key`,
                         you can request contents of any nested folder.
            :param limit: number of children resources to be included in the response
            :param offset: number of children resources to be skipped in the response
            :param preview_size: size of the file preview
            :param preview_crop: `bool`, cut the preview to the size specified in the `preview_size`
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises WrongResourceTypeError: resource is not a directory

            :returns: generator of :any:`PublicResourceObject`
        """

        _apply_default_args(kwargs, self.default_args)

        return _listdir(self.get_public_meta, public_key, **kwargs)

    async def get_public_type(self, public_key: str, /, **kwargs) -> str:
        """
            Get public resource type.

            :param public_key: public key or public URL of the resource
            :param path: relative path to the resource within the public folder
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: "file" or "dir"
        """

        _apply_default_args(kwargs, self.default_args)

        return await _get_type(self.get_public_meta, public_key, **kwargs)

    async def is_public_dir(self, public_key: str, /, **kwargs) -> bool:
        """
            Check whether `public_key` is a public directory.

            :param public_key: public key or public URL of the resource
            :param path: relative path to the resource within the public folder
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: `True` if `public_key` is a directory, `False` otherwise (even if it doesn't exist)
        """

        _apply_default_args(kwargs, self.default_args)

        try:
            return (await self.get_public_type(public_key, **kwargs)) == "dir"
        except PathNotFoundError:
            return False

    async def is_public_file(self, public_key: str, /, **kwargs) -> bool:
        """
            Check whether `public_key` is a public file.

            :param public_key: public key or public URL of the resource
            :param path: relative path to the resource within the public folder
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: `True` if `public_key` is a file, `False` otherwise (even if it doesn't exist)
        """

        _apply_default_args(kwargs, self.default_args)

        try:
            return (await self.get_public_type(public_key, **kwargs)) == "file"
        except PathNotFoundError:
            return False

    async def trash_listdir(self, path: str, /, **kwargs) -> AsyncGenerator["TrashResourceObject", None]:
        """
            Get contents of a trash resource.

            :param path: path to the directory in the trash bin
            :param limit: number of children resources to be included in the response
            :param offset: number of children resources to be skipped in the response
            :param preview_size: size of the file preview
            :param preview_crop: `bool`, cut the preview to the size specified in the `preview_size`
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises WrongResourceTypeError: resource is not a directory

            :returns: generator of :any:`TrashResourceObject`
        """

        _apply_default_args(kwargs, self.default_args)

        return _listdir(self.get_trash_meta, path, **kwargs)

    async def get_trash_type(self, path: str, /, **kwargs) -> str:
        """
            Get trash resource type.

            :param path: path to the trash resource
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: "file" or "dir"
        """

        _apply_default_args(kwargs, self.default_args)

        return await _get_type(self.get_trash_meta, path, **kwargs)

    async def is_trash_dir(self, path: str, /, **kwargs) -> bool:
        """
            Check whether `path` is a trash directory.

            :param path: path to the trash resource
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: `True` if `path` is a directory, `False` otherwise (even if it doesn't exist)
        """

        _apply_default_args(kwargs, self.default_args)

        try:
            return (await self.get_trash_type(path, **kwargs)) == "dir"
        except PathNotFoundError:
            return False

    async def is_trash_file(self, path: str, /, **kwargs) -> bool:
        """
            Check whether `path` is a trash file.

            :param path: path to the trash resource
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: `True` if `path` is a directory, `False` otherwise (even if it doesn't exist)
        """

        _apply_default_args(kwargs, self.default_args)

        try:
            return (await self.get_trash_type(path, **kwargs)) == "file"
        except PathNotFoundError:
            return False

    async def get_public_resources(self, **kwargs) -> "PublicResourcesListObject":
        """
            Get a list of public resources.

            :param offset: offset from the beginning of the list
            :param limit: maximum number of elements in the list
            :param preview_size: size of the file preview
            :param preview_crop: `bool`, cut the preview to the size specified in the `preview_size`
            :param type: filter based on type of resources ("file" or "dir")
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: :any:`PublicResourcesListObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = GetPublicResourcesRequest(self.get_session(), **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def patch(self, path: str, properties: dict, /, **kwargs) -> "ResourceObject":
        """
            Update custom properties of a resource.

            :param path: path to the resource
            :param properties: `dict`, custom properties to update
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: :any:`ResourceObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = PatchRequest(self.get_session(), path, properties, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def get_files(self, **kwargs) -> AsyncGenerator["ResourceObject", None]:
        """
            Get a flat list of all files (that doesn't include directories).

            :param offset: offset from the beginning of the list
            :param limit: number of list elements to be included
            :param media_type: type of files to include in the list
            :param sort: `str`, field to be used as a key to sort children resources
            :param preview_size: size of the file preview
            :param preview_crop: `bool`, cut the preview to the size specified in the `preview_size`
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: generator of :any:`ResourceObject`
        """

        _apply_default_args(kwargs, self.default_args)

        if kwargs.get("limit") is not None:
            request = FilesRequest(self.get_session(), **kwargs)
            await request.send()

            for i in (await request.process(yadisk=self)).items:
                yield i

            return

        kwargs.setdefault("offset", 0)
        kwargs["limit"] = 1000

        while True:
            counter = 0
            async for i in self.get_files(**kwargs):
                counter += 1
                yield i

            if counter < kwargs["limit"]:
                break

            kwargs["offset"] += kwargs["limit"]

    async def get_last_uploaded(self, **kwargs) -> AsyncGenerator["ResourceObject", None]:
        """
            Get the list of latest uploaded files sorted by upload date.

            :param limit: maximum number of elements in the list
            :param media_type: type of files to include in the list
            :param preview_size: size of the file preview
            :param preview_crop: `bool`, cut the preview to the size specified in the `preview_size`
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ForbiddenError: application doesn't have enough rights for this request

            :returns: generator of :any:`ResourceObject`
        """

        _apply_default_args(kwargs, self.default_args)

        request = LastUploadedRequest(self.get_session(), **kwargs)
        await request.send()

        for i in (await request.process(yadisk=self)).items:
            yield i

    async def upload_url(self, url: str, path: str, /, **kwargs) -> "OperationLinkObject":
        """
            Upload a file from URL.

            :param url: source URL
            :param path: destination path
            :param disable_redirects: `bool`, forbid redirects
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises ParentNotFoundError: parent directory doesn't exist
            :raises PathExistsError: destination path already exists
            :raises InsufficientStorageError: cannot upload file due to lack of storage space
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request
            :raises UploadTrafficLimitExceededError: upload limit has been exceeded

            :returns: :any:`OperationLinkObject`, link to the asynchronous operation
        """

        _apply_default_args(kwargs, self.default_args)

        request = UploadURLRequest(self.get_session(), url, path, **kwargs)
        await request.send()

        return await request.process(yadisk=self)

    async def get_public_download_link(self, public_key: str, /, **kwargs) -> str:
        """
            Get a download link for a public resource.

            :param public_key: public key or public URL of the resource
            :param path: relative path to the resource within the public folder
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: `str`
        """

        _apply_default_args(kwargs, self.default_args)

        request = GetPublicDownloadLinkRequest(self.get_session(), public_key, **kwargs)
        await request.send()

        return (await request.process(yadisk=self)).href

    async def download_public(self,
                              public_key: str,
                              file_or_path: Union[str, bytes, IO], /, **kwargs) -> PublicResourceLinkObject:
        """
            Download the public resource.

            :param public_key: public key or public URL of the resource
            :param file_or_path: destination path or file-like object
            :param path: relative path to the resource within the public folder
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises PathNotFoundError: resource was not found on Disk
            :raises ForbiddenError: application doesn't have enough rights for this request
            :raises ResourceIsLockedError: resource is locked by another request

            :returns: :any:`PublicResourceLinkObject`
        """

        _apply_default_args(kwargs, self.default_args)

        await self._download(
            lambda *args, **kwargs: self.get_public_download_link(public_key),
            "", file_or_path, **kwargs)
        return PublicResourceLinkObject.from_public_key(public_key, yadisk=self)

    async def get_operation_status(self, operation_id, **kwargs):
        """
            Get operation status.

            :param operation_id: ID of the operation or a link
            :param fields: list of keys to be included in the response
            :param timeout: `float` or :any:`aiohttp.ClientTimeout`, request timeout
            :param headers: `dict` or `None`, additional request headers
            :param n_retries: `int`, maximum number of retries
            :param retry_interval: delay between retries in seconds

            :raises OperationNotFoundError: requested operation was not found

            :returns: `str`
        """

        _apply_default_args(kwargs, self.default_args)

        return await self._get_operation_status(self.get_session(), operation_id, **kwargs)

    async def _get_operation_status(self, session: SessionWithHeaders, operation_id: str, **kwargs) -> str:
        request = GetOperationStatusRequest(session, operation_id, **kwargs)
        await request.send()

        return (await request.process()).status

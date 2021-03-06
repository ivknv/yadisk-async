#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import os
import http3
import random
import tempfile

import posixpath
from unittest import TestCase
from io import BytesIO

import yadisk_async.settings

yadisk_async.settings.DEFAULT_N_RETRIES = 50
yadisk_async.settings.DEFAULT_UPLOAD_N_RETRIES = 50

original_send = http3.AsyncClient.send

async def patched_send(self, *args, **kwargs):
    # Fake a random server error
    if random.randint(1, 5) == 1:
        raise yadisk_async.exceptions.InternalServerError()

    response = await original_send(self, *args, **kwargs)

    return response

http3.AsyncClient.send = patched_send

if not os.environ.get("PYTHON_YADISK_APP_TOKEN"):
    raise ValueError("Environment variable PYTHON_YADISK_APP_TOKEN must be set")

if not os.environ.get("PYTHON_YADISK_TEST_ROOT"):
    raise ValueError("Environment variable PYTHON_YADISK_TEST_ROOT must be set")

def async_test(f):
    def wrapper(*args, **kwargs):
        coroutine = asyncio.coroutine(f)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coroutine(*args, **kwargs))

    return wrapper

class ResourcesTestCase(TestCase):
    def __init__(self, *args, **kwargs):
        self.yadisk = None

        TestCase.__init__(self, *args, **kwargs)

        self.yadisk = yadisk_async.YaDisk(os.environ.get("PYTHON_YADISK_APP_ID"),
                                          os.environ.get("PYTHON_YADISK_APP_SECRET"),
                                          os.environ.get("PYTHON_YADISK_APP_TOKEN"))

        self.path = os.environ.get("PYTHON_YADISK_TEST_ROOT")

    def __del__(self):
        if self.yadisk is None:
            return

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.yadisk.close())

    @async_test
    async def test_get_meta(self):
       self.assertIsInstance(await self.yadisk.get_meta(self.path), yadisk_async.objects.ResourceObject)

    def test_listdir(self):
        names = ["dir1", "dir2", "dir3"]
        paths = [posixpath.join(self.path, name) for name in names]
        mkdir_tasks = [self.yadisk.mkdir(path) for path in paths]

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*mkdir_tasks))

        async def get_result():
            return [i.name async for i in await self.yadisk.listdir(self.path)]

        result = loop.run_until_complete(get_result())

        remove_tasks = [self.yadisk.remove(path, permanently=True) for path in paths]

        loop.run_until_complete(asyncio.gather(*remove_tasks))

        self.assertEqual(result, names)

    def test_listdir_fields(self):
        names = ["dir1", "dir2", "dir3"]
        paths = [posixpath.join(self.path, name) for name in names]
        mkdir_tasks = [self.yadisk.mkdir(path) for path in paths]

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*mkdir_tasks))

        async def get_result():
            return [(i.name, i.type, i.file)
                    async for i in await self.yadisk.listdir(self.path, fields=["name", "type"])]

        result = loop.run_until_complete(get_result())

        remove_tasks = [self.yadisk.remove(path, permanently=True) for path in paths]

        loop.run_until_complete(asyncio.gather(*remove_tasks))

        self.assertEqual(result, [(name, "dir", None) for name in names])

    @async_test
    async def test_listdir_on_file(self):
        buf = BytesIO()
        buf.write(b"0" * 1000)
        buf.seek(0)

        path = posixpath.join(self.path, "zeroes.txt")

        await self.yadisk.upload(buf, path)

        with self.assertRaises(yadisk_async.exceptions.WrongResourceTypeError):
            [i async for i in await self.yadisk.listdir(path)]

        await self.yadisk.remove(path)

    def test_listdir_with_limits(self):
        names = ["dir1", "dir2", "dir3"]
        paths = [posixpath.join(self.path, name) for name in names]
        mkdir_tasks = [self.yadisk.mkdir(path) for path in paths]

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*mkdir_tasks))

        async def get_result():
            return [i.name async for i in await self.yadisk.listdir(self.path, limit=1)]

        result = loop.run_until_complete(get_result())

        remove_tasks = [self.yadisk.remove(path, permanently=True) for path in paths]

        loop.run_until_complete(asyncio.gather(*remove_tasks))

        self.assertEqual(result, names)

    def test_mkdir_and_exists(self):
        names = ["dir1", "dir2", "dir3"]
        paths = [posixpath.join(self.path, name) for name in names]

        async def check_existence(path):
            await self.yadisk.mkdir(path)
            self.assertTrue(await self.yadisk.exists(path))

            await self.yadisk.remove(path, permanently=True)
            self.assertFalse(await self.yadisk.exists(path))

        tasks = [check_existence(path) for path in paths]

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))

    @async_test
    async def test_upload_and_download(self):
        buf1 = BytesIO()
        buf2 = tempfile.NamedTemporaryFile("w+b")

        orig_close = buf1.close

        def wrapper():
            raise BaseException("WHERERA")
            orig_close()

        buf1.close = wrapper

        buf1.write(b"0" * 1024**2)
        buf1.seek(0)

        path = posixpath.join(self.path, "zeroes.txt")

        await self.yadisk.upload(buf1, path, overwrite=True, n_retries=50)
        await self.yadisk.download(path, buf2.name, n_retries=50)
        await self.yadisk.remove(path, permanently=True)

        buf1.seek(0)
        buf2.seek(0)

        self.assertEqual(buf1.read(), buf2.read())

    @async_test
    async def test_check_token(self):
        self.assertTrue(await self.yadisk.check_token())
        self.assertFalse(await self.yadisk.check_token("asdasdasd"))

    @async_test
    async def test_permanent_remove(self):
        path = posixpath.join(self.path, "dir")

        await self.yadisk.mkdir(path)
        await self.yadisk.remove(path, permanently=True)
        self.assertFalse(await self.yadisk.trash_exists(path))

    @async_test
    async def test_restore_trash(self):
        path = posixpath.join(self.path, "dir")

        await self.yadisk.mkdir(path)
        await self.yadisk.remove(path)
        await self.yadisk.restore_trash("dir", path)
        self.assertTrue(await self.yadisk.exists(path))
        await self.yadisk.remove(path, permanently=True)

    @async_test
    async def test_move(self):
        path1 = posixpath.join(self.path, "dir1")
        path2 = posixpath.join(self.path, "dir2")
        await self.yadisk.mkdir(path1)
        await self.yadisk.move(path1, path2)

        self.assertTrue(await self.yadisk.exists(path2))

        await self.yadisk.remove(path2, permanently=True)

    @async_test
    async def test_remove_trash(self):
        path = posixpath.join(self.path, "dir-to-remove")
        await self.yadisk.mkdir(path)
        await self.yadisk.remove(path)
        await self.yadisk.remove_trash("dir-to-remove")
        self.assertFalse(await self.yadisk.trash_exists("dir-to-remove"))

    @async_test
    async def test_publish_unpublish(self):
        path = self.path

        await self.yadisk.publish(path)
        self.assertIsNotNone((await self.yadisk.get_meta(path)).public_url)

        await self.yadisk.unpublish(path)
        self.assertIsNone((await self.yadisk.get_meta(path)).public_url)

    @async_test
    async def test_patch(self):
        path = self.path

        await self.yadisk.patch(path, {"test_property": "I'm a value!"})
        self.assertEqual((await self.yadisk.get_meta(path)).custom_properties["test_property"], "I'm a value!")

        await self.yadisk.patch(path, {"test_property": None})
        self.assertIsNone((await self.yadisk.get_meta(path)).custom_properties)

    @async_test
    async def test_issue7(self):
        # See https://github.com/ivknv/yadisk/issues/7

        try:
            await self.yadisk.public_listdir("any value here", path="any value here")
        except yadisk_async.exceptions.PathNotFoundError:
            pass

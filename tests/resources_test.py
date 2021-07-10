#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import os
import random
import tempfile

import posixpath
from unittest import TestCase
from io import BytesIO

import yadisk_async.settings

yadisk_async.settings.DEFAULT_N_RETRIES = 50
yadisk_async.settings.DEFAULT_UPLOAD_N_RETRIES = 50

def async_test(f):
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(f(*args, **kwargs))

    return wrapper

class ResourcesTestCase(TestCase):
    def __init__(self, *args, **kwargs):
        self.yadisk = None

        TestCase.__init__(self, *args, **kwargs)

        if not os.environ.get("PYTHON_YADISK_APP_TOKEN"):
            raise ValueError("Environment variable PYTHON_YADISK_APP_TOKEN must be set")

        if not os.environ.get("PYTHON_YADISK_TEST_ROOT"):
            raise ValueError("Environment variable PYTHON_YADISK_TEST_ROOT must be set")

        self.yadisk = yadisk_async.YaDisk(os.environ.get("PYTHON_YADISK_APP_ID"),
                                          os.environ.get("PYTHON_YADISK_APP_SECRET"),
                                          os.environ.get("PYTHON_YADISK_APP_TOKEN"))

        self.path = os.environ.get("PYTHON_YADISK_TEST_ROOT")

        # Get rid of 'disk:/' prefix in the path and make it start with a slash
        # for consistency
        if self.path.startswith("disk:/"):
            self.path = posixpath.join("/", self.path[len("disk:/"):])

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

        await self.yadisk.remove(path, permanently=True)

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
        origin_path = "disk:" + path

        await self.yadisk.mkdir(path)
        await self.yadisk.remove(path, permanently=True)

        async for i in await self.yadisk.trash_listdir("/"):
            self.assertFalse(i.origin_path == origin_path)

    @async_test
    async def test_restore_trash(self):
        path = posixpath.join(self.path, "dir")
        origin_path = "disk:" + path

        await self.yadisk.mkdir(path)
        await self.yadisk.remove(path)

        trash_path = None

        async for i in await self.yadisk.trash_listdir("/"):
            if i.origin_path == origin_path:
                trash_path = i.path
                break

        self.assertTrue(trash_path is not None)

        await self.yadisk.restore_trash(trash_path, path)
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
        origin_path = "disk:" + path

        await self.yadisk.mkdir(path)
        await self.yadisk.remove(path)

        trash_path = None

        async for i in await self.yadisk.trash_listdir("/"):
            if i.origin_path == origin_path:
                trash_path = i.path
                break

        self.assertTrue(trash_path is not None)

        await self.yadisk.remove_trash(trash_path)
        self.assertFalse(await self.yadisk.trash_exists(trash_path))

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

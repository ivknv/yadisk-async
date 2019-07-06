Introduction
============

.. _YaDisk: https://github.com/ivknv/yadisk

YaDisk-async is a modified version of `YaDisk`_ with :code:`async/await` support.
It uses `aiohttp` instead of `requests`.

The usage is more or less the same, except that you have to manually close
all the sessions (can be done with :any:`YaDisk.close` or through :code:`async with` statement).

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
    with open("file_to_upload.txt", "rb") as f:
        await y.upload(f, "/destination.txt")

    # Download "/some-file-to-download.txt" to "downloaded.txt"
    await y.download("/some-file-to-download.txt", "downloaded.txt")

    # Permanently remove "/file-to-remove"
    await y.remove("/file-to-remove", permanently=True)

    # Create a new directory at "/test-dir"
    print(await y.mkdir("/test-dir"))

    # Always remember to close all the connections or you'll get a warning
    await y.close()

Receiving token with confirmation code
######################################

.. code:: python

    import asyncio
    import sys
    import yadisk_async

    async def main():
        async with yadisk_async.YaDisk("application-id>", "<application-secret>") as y:
            url = y.get_code_url()

            print("Go to the following url: %s" % url)
            code = input("Enter the confirmation code: ")

            try:
                response = await y.get_token(code)
            except yadisk_async.exceptions.BadRequestError:
                print("Bad code")
                sys.exit(1)

            y.token = response.access_token

            if await y.check_token():
                print("Sucessfully received token!")
            else:
                print("Something went wrong. Not sure how though...")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

Recursive upload
################

.. code:: python

    import asyncio
    import posixpath
    import os
    import yadisk_async

    def recursive_upload(from_dir, to_dir, n_parallel_requests=5):
        loop = asyncio.get_event_loop()

        y = yadisk_async.YaDisk(token="<application-token>")

        try:
            async def upload_files(queue):
                while queue:
                    in_path, out_path = queue.pop(0)

                    print("Uploading %s -> %s" % (in_path, out_path))

                    try:
                        await y.upload(in_path, out_path)
                    except yadisk_async.exceptions.PathExistsError:
                        print("%s already exists" % (out_path,))

            async def create_dirs(queue):
                while queue:
                    path = queue.pop(0)

                    print("Creating directory %s" % (path,))

                    try:
                        await y.mkdir(path)
                    except yadisk_async.exceptions.PathExistsError:
                        print("%s already exists" % (path,))

            mkdir_queue = []
            upload_queue = []

            print("Creating directory %s" % (to_dir,))

            try:
                loop.run_until_complete(y.mkdir(to_dir))
            except yadisk_async.exceptions.PathExistsError:
                print("%s already exists" % (to_dir,))

            for root, dirs, files in os.walk(from_dir):
                rel_dir_path = root.split(from_dir)[1].strip(os.path.sep)
                rel_dir_path = rel_dir_path.replace(os.path.sep, "/")
                dir_path = posixpath.join(to_dir, rel_dir_path)

                for dirname in dirs:
                    mkdir_queue.append(posixpath.join(dir_path, dirname))

                for filename in files:
                    out_path = posixpath.join(dir_path, filename)
                    rel_dir_path_sys = rel_dir_path.replace("/", os.path.sep)
                    in_path = os.path.join(from_dir, rel_dir_path_sys, filename)

                    upload_queue.append((in_path, out_path))

                tasks = [upload_files(upload_queue) for i in range(n_parallel_requests)]
                tasks.extend(create_dirs(mkdir_queue) for i in range(n_parallel_requests))

                loop.run_until_complete(asyncio.gather(*tasks))
        finally:
            loop.run_until_complete(y.close())

    from_dir = input("Directory to upload: ")
    to_dir = input("Destination directory: ")

    recursive_upload(from_dir, to_dir, 5)

Setting custom properties of files
##################################

.. code:: python

    import yadisk_async

    async def main():
        async with yadisk_async.YaDisk(token="<application-token>") as y:
            path = input("Enter a path to patch: ")
            properties = {"speed_of_light":       299792458,
                          "speed_of_light_units": "meters per second",
                          "message_for_owner":    "MWAHAHA! Your file has been patched by an evil script!"}

            meta = await y.patch(path, properties)
            print("\nNew properties: ")

            for k, v in meta.custom_properties.items():
                print("%s: %r" % (k, v))

            answer = input("\nWant to get rid of them? (y/[n]) ")

            if answer.lower() in ("y", "yes"):
                properties = {k: None for k in properties}
                await y.patch(path, properties)
                print("Everything's back as usual")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

Emptying the trash bin
######################

.. code:: python

    import asyncio
    import sys
    import yadisk_async

    async def main():
        async with yadisk_async.YaDisk(token="<application-token>") as y:
            answer = input("Are you sure about this? (y/[n]) ")

            if answer.lower() in ("y", "yes"):
                print("Emptying the trash bin...")
                operation = await y.remove_trash("/")
                print("It might take a while...")

                if operation is None:
                    print("Nevermind. The deed is done.")
                    sys.exit(0)

                while True:
                    status = await y.get_operation_status(operation.href)

                    if status == "in-progress":
                        await asyncio.sleep(5)
                        print("Still waiting...")
                    elif status == "success":
                        print("Success!")
                        break
                    else:
                        print("Got some weird status: %r" % (status,))
                        print("That's not normal")
                        break
            else:
                print("Not going to do anything")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

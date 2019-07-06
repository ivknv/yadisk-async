#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os

from setuptools import setup, find_packages

module_dir = os.path.dirname(__file__)

with codecs.open(os.path.join(module_dir, "README.rst"), encoding="utf8") as f:
    long_description = f.read()

setup(name="yadisk-async",
      version="1.3.0",
      packages=find_packages(exclude=("tests",)),
      description="Библиотека-клиент REST API Яндекс.Диска с поддержкой async/await / Yandex.Disk REST API client library with async/await support",
      long_description=long_description,
      author="Ivan Konovalov",
      author_email="ivknv0@gmail.com",
      license="LGPLv3",
      python_requires=">=3.6",
      install_requires=["aiohttp"],
      url="https://github.com/ivknv/yadisk-async",
      project_urls={"Source code": "https://github.com/ivknv/yadisk-async",
                    "Documentation (EN)": "https://yadisk-async.readthedocs.io/en/latest",
                    "Documentation (RU)": "https://yadisk-async.readthedocs.io/ru/latest",
                    "Bug tracker": "https://github.com/ivknv/yadisk-async/issues"},
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
          "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Operating System :: OS Independent",
          "Topic :: Internet",
          "Topic :: Software Development :: Libraries",
          "Topic :: Software Development :: Libraries :: Python Modules"],
      keywords="yandex yandex.disk rest async")

import os
import sys
from setuptools import setup, find_packages # Consolidated setuptools import

VERSION = "1.8.0"
py_vers_tag = "-%s.%s" % sys.version_info[:2]

test_dirs = ["functional_tests", "unit_tests", os.path.join("doc", "doc_tests"), "nose"]

# try...except ImportError block and setup3lib import removed

addl_args = dict(
    zip_safe=False,
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "nosetests = nose:run_exit",
            "nosetests%s = nose:run_exit" % py_vers_tag,
        ],
        "setuptools.commands": [
            " nosetests = nose.commands:nosetests",
        ],
    },
    test_suite="nose.collector",
)

# Windows-specific easy_install patching removed

test_deps = [
    "coverage",
    "sphinx",
]

setup(
    name="nose-py3",
    version=VERSION,
    author="Adam Bilbrough",
    author_email="",
    maintainer="Adam Bilbrough",
    extras_require={
        "test": test_deps,
    },
    tests_require=test_deps,
    description="nose extends unittest to make testing easier - python3 version",
    long_description="""nose extends the test loading and running features of unittest, making
        it easier to write, find and run tests.

        By default, nose will run tests in files or directories under the current
        working directory whose names include "test" or "Test" at a word boundary
        (like "test_this" or "functional_test" or "TestClass" but not
        "libtest"). Test output is similar to that of unittest, but also includes
        captured stdout output from failing tests, for easy print-style debugging.

        These features, and many more, are customizable through the use of
        plugins. Plugins included with nose provide support for doctest, code
        coverage and profiling, flexible attribute-based test selection,
        output capture and more. More information about writing plugins may be
        found on in the nose API documentation, here:
        http://readthedocs.org/docs/nose/

        If you have recently reported a bug marked as fixed, or have a craving for
        the very latest, you may want the development version instead:
        https://github.com/atsb/nose-py3
        """,
    license="GNU LGPL",
    keywords="test unittest doctest automatic discovery",
    url="https://github.com/atsb/nose-py3",
    data_files=[("man/man1", ["nosetests.1"])],
    package_data={"": ["*.txt", "examples/*.py", "examples/*/*.py"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Testing",
    ],
    **addl_args
)

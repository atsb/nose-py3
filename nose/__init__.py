from nose.core import collector, main, run, run_exit, runmodule
from nose.plugins.deprecated import DeprecatedTest
from nose.plugins.skip import SkipTest
from nose.tools import with_setup

__author__ = 'Adam Bilbrough'
__versioninfo__ = (1, 8, 0)
__version__ = '.'.join(map(str, __versioninfo__))

__all__ = [
    'main', 'run', 'run_exit', 'runmodule', 'with_setup',
    'SkipTest', 'DeprecatedTest', 'collector'
    ]

import logging
import os
import re
import shutil
import sys

from setuptools import Command
from setuptools import Distribution as _Distribution
from setuptools import setup as _setup

import patch

py3_args = ['test_dirs', 'test_build_dir', 'doctest_exts', 'pyversion_patching']
patch.logger.setLevel(logging.WARN)
patchfile_re = re.compile(r'(.*)\.py([0-9.]+)\.patch$')


def pyversion_patch(filename):
    """
    :param filename:
    :return:
    Find the best pyversion-fixup patch for a given filename and apply it.
    """
    dir, file = os.path.split(filename)
    best_ver = (0,)
    patchfile = None
    for dirfile in os.listdir(dir):
        m = patchfile_re.match(dirfile)
        if not m:
            continue
        base, ver = m.groups()
        if base != file:
            continue
        ver = tuple([int(v) for v in ver.split('.')])
        if sys.version_info >= ver and ver > best_ver:
            best_ver = ver
            patchfile = dirfile
    if not patchfile:
        return False
    logging.info("Applying %s to %s..." % (patchfile, filename))
    cwd = os.getcwd()
    os.chdir(dir)
    try:
        p = patch.fromfile(patchfile)
        p.apply()
    finally:
        os.chdir(cwd)
    return True


class Distribution(_Distribution):
    def __init__(self, attrs=None):
        self.test_dirs = []
        self.test_build_dir = None
        self.doctest_exts = ['.py', '.rst']
        self.pyversion_patching = False
        _Distribution.__init__(self, attrs)


class BuildTestsCommand(Command):
    user_options = []

    def initialize_options(self):
        self.test_base = None

    def finalize_options(self):
        test_base = self.distribution.test_build_dir
        if not test_base:
            bcmd = self.get_finalized_command('build')
            test_base = bcmd.build_base
        self.test_base = test_base

    def run(self):
        test_dirs = getattr(self.distribution, 'test_dirs', [])
        test_base = self.test_base
        bpy_cmd = self.get_finalized_command("build_py")
        lib_base = os.path.normpath(bpy_cmd.build_lib)
        modified = []
        py_modified = []
        doc_modified = []
        os.makedirs(test_base)
        for testdir in test_dirs:
            for srcdir, dirnames, filenames in os.walk(testdir):
                destdir = os.path.join(test_base, srcdir)
                os.makedirs(destdir)
                for fn in filenames:
                    if fn.startswith("."):
                        # Skip .svn folders and such
                        continue
                    dstfile, copied = shutil.copyfile(
                        os.path.join(srcdir, fn),
                        os.path.join(destdir, fn))
                    if copied:
                        modified.append(dstfile)
                        if fn.endswith('.py'):
                            py_modified.append(dstfile)
                        for ext in self.distribution.doctest_exts:
                            if fn.endswith(ext):
                                doc_modified.append(dstfile)
                                break

        if self.distribution.pyversion_patching:
            if patch is not None:
                for file in modified:
                    pyversion_patch(file)
            else:
                logging.warn(
                    "Warning: pyversion_patching specified in setup config but patch module not found.  Patching "
                    "will not be performed.")

        os.makedirs(lib_base)
        self.reinitialize_command('egg_info', egg_base=lib_base)
        self.run_command('egg_info')


def setup(*args, **kwargs):
    kwargs.setdefault('distclass', Distribution)
    cmdclass = kwargs.setdefault('cmdclass', {})
    cmdclass.setdefault('build_tests', BuildTestsCommand)
    return _setup(*args, **kwargs)

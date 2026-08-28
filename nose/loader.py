"""
Test Loader
-----------

nose's test loader implements the same basic functionality as its
superclass, unittest.TestLoader, but extends it by more liberal
interpretations of what may be a test and how a test may be named.
"""
import logging
import os
import sys
import types
import unittest
from inspect import isfunction

from nose.case import FunctionTestCase, MethodTestCase
from nose.config import Config
from nose.failure import Failure
from nose.importer import Importer, add_path, remove_path
from nose.pyversion import sort_list, cmp_to_key
from nose.pyversion import unbound_method, ismethod
from nose.selector import defaultSelector, TestAddress
from nose.suite import ContextSuiteFactory, ContextList, LazySuite
from nose.util import (
    func_lineno,
    getpackage,
    isclass,
    isgenerator,
    ispackage,
    regex_last_key,
    resolve_name,
    src,
    transplant_func,
    transplant_class,
    test_address,
)

log = logging.getLogger(__name__)
# log.setLevel(logging.DEBUG)

# for efficiency and easier mocking
op_normpath = os.path.normpath
op_abspath = os.path.abspath
op_join = os.path.join
op_isdir = os.path.isdir
op_isfile = os.path.isfile

__all__ = ['TestLoader', 'defaultTestLoader']


class TestLoader(unittest.TestLoader):
    """Test loader that extends unittest.TestLoader to:

    * Load tests from test-like functions and classes that are not
      unittest.TestCase subclasses
    * Find and load test modules in a directory
    * Support tests that are generators
    * Support easy extensions of or changes to that behavior through plugins
    """

    config = None
    importer = None
    workingDir = None
    selector = None
    suiteClass = None

    def __init__(self, config=None, importer=None, workingDir=None,
                 selector=None):
        """Initialize a test loader.

        Parameters (all optional):

        * config: provide a `nose.config.Config`_ or other config class
          instance; if not provided a `nose.config.Config`_ with
          default values is used.
        * importer: provide an importer instance that implements
          `importFromPath`. If not provided, a
          `nose.importer.Importer`_ is used.
        * workingDir: the directory to which file and module names are
          relative. If not provided, assumed to be the current working
          directory.
        * selector: a selector class or instance. If a class is
          provided, it will be instantiated with one argument, the
          current config. If not provided, a `nose.selector.Selector`_
          is used.
        """
        if config is None:
            config = Config()
        if importer is None:
            importer = Importer(config=config)
        if workingDir is None:
            workingDir = config.workingDir
        if selector is None:
            selector = defaultSelector(config)
        elif isclass(selector):
            selector = selector(config)
        self.config = config
        self.importer = importer
        self.workingDir = op_normpath(op_abspath(workingDir))
        self.selector = selector
        if config.addPaths:
            add_path(workingDir, config)
        self.suiteClass = ContextSuiteFactory(config=config)

        self._visitedPaths = set()

        super().__init__()

    def getTestCaseNames(self, testCaseClass):
        """Override to select with selector, unless
        config.getTestCaseNamesCompat is True
        """
        if self.config.getTestCaseNamesCompat:
            return super().getTestCaseNames(testCaseClass)

        def wanted(attr, cls=testCaseClass, sel=self.selector):
            item = getattr(cls, attr, None)
            if isfunction(item):
                item = unbound_method(cls, item)
            elif not ismethod(item):
                return False
            return sel.wantMethod(item)

        cases = list(filter(wanted, dir(testCaseClass)))

        # add runTest if nothing else picked
        if not cases and hasattr(testCaseClass, 'runTest'):
            cases = ['runTest']
        if self.sortTestMethodsUsing:
            cases = sort_list(cases, cmp_to_key(self.sortTestMethodsUsing))
        return cases

    def _haveVisited(self, path):
        # For cases where path is None, we always pretend we haven't visited
        # them.
        if path is None:
            return False

        return path in self._visitedPaths

    def _addVisitedPath(self, path):
        if path is not None:
            self._visitedPaths.add(path)

    def loadTestsFromDir(self, path):
        """Load tests from the directory at path. This is a generator
        -- each suite of tests from a module or other file is yielded
        and is expected to be executed before the next file is
        examined.
        """
        log.debug("load from dir %s", path)
        plugins = self.config.plugins
        plugins.beforeDirectory(path)
        paths_added = []
        if self.config.addPaths:
            paths_added = add_path(path, self.config)

        entries = os.listdir(path)
        entries = sort_list(entries, regex_last_key(self.config.testMatch))
        for entry in entries:
            if entry.startswith('.'):
                continue
            if src(entry) == '__init__.py':
                continue
            entry_path = op_abspath(op_join(path, entry))
            is_file = op_isfile(entry_path)
            wanted = False
            if is_file:
                is_dir = False
                wanted = self.selector.wantFile(entry_path)
            else:
                is_dir = op_isdir(entry_path)
                if is_dir:
                    if entry.startswith('_'):
                        continue
                    wanted = self.selector.wantDirectory(entry_path)
            is_package = ispackage(entry_path)

            if wanted and not self._haveVisited(entry_path):
                self._addVisitedPath(entry_path)
                if is_file:
                    plugins.beforeContext()
                    if entry.endswith('.py'):
                        yield self.loadTestsFromName(
                            entry_path, discovered=True)
                    else:
                        yield self.loadTestsFromFile(entry_path)
                    plugins.afterContext()
                elif is_package:
                    yield self.loadTestsFromName(
                        entry_path, discovered=True)
                else:
                    yield self.suiteClass(
                        lambda: self.loadTestsFromDir(entry_path))

        tests = []
        for test in plugins.loadTestsFromDir(path):
            tests.append(test)

        try:
            if tests:
                yield self.suiteClass(tests)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            yield self.suiteClass([Failure(*sys.exc_info())])
        finally:
            if self.config.addPaths:
                for p in paths_added:
                    remove_path(p)
            plugins.afterDirectory(path)

    def loadTestsFromFile(self, filename):
        """Load tests from a non-module file. Default is to raise a
        ValueError; plugins may implement `loadTestsFromFile` to
        provide a list of tests loaded from the file.
        """
        log.debug("Load from non-module file %s", filename)
        try:
            tests = [
                test
                for test in self.config.plugins.loadTestsFromFile(filename)
            ]
            if tests:
                tests = list(filter(None, tests))
                return self.suiteClass(tests)

            with open(filename, 'r'):
                pass
            raise ValueError("Unable to load tests from file %s" % filename)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            exc = sys.exc_info()
            return self.suiteClass(
                [Failure(exc[0], exc[1], exc[2],
                         address=(filename, None, None))])

    def loadTestsFromGenerator(self, generator, module):
        """Lazy-load tests from a generator function. The generator function
        may yield either:

        * a callable, or
        * a function name resolvable within the same module
        """

        def generate(g=generator, m=module):
            try:
                for test in g():
                    test_func, arg = self.parseGeneratedTest(test)
                    if not callable(test_func):
                        test_func = getattr(m, test_func)
                    yield FunctionTestCase(test_func, arg=arg, descriptor=g)
            except KeyboardInterrupt:
                raise
            except Exception:
                exc = sys.exc_info()
                yield Failure(exc[0], exc[1], exc[2],
                              address=test_address(generator))

        return self.suiteClass(generate, context=generator, can_split=False)

    def loadTestsFromGeneratorMethod(self, generator, cls):
        """Lazy-load tests from a generator method.

        This is more complicated than loading from a generator function,
        since a generator method may yield:

        * a function
        * a bound or unbound method, or
        * a method name
        """
        if hasattr(generator, '__self__'):
            cls = generator.__self__.__class__
        inst = cls()
        method = generator.__name__
        generator = getattr(inst, method)

        def generate(g=generator, c=cls):
            try:
                for test in g():
                    test_func, arg = self.parseGeneratedTest(test)
                    if not callable(test_func):
                        test_func = unbound_method(c, getattr(c, test_func))
                    if ismethod(test_func):
                        yield MethodTestCase(test_func, arg=arg, descriptor=g)
                    elif callable(test_func):
                        yield MethodTestCase(g, test=test_func, arg=arg)
                    else:
                        yield Failure(
                            TypeError,
                            "%s is not a callable or method" % test_func)
            except KeyboardInterrupt:
                raise
            except Exception:
                exc = sys.exc_info()
                yield Failure(exc[0], exc[1], exc[2],
                              address=test_address(generator))

        return self.suiteClass(generate, context=generator, can_split=False)

    def loadTestsFromModule(self, module, path=None, discovered=False):
        """Load all tests from module and return a suite containing
        them. If the module has been discovered and is not test-like,
        the suite will be empty by default, though plugins may add
        their own tests.
        """
        log.debug("Load from module %s", module)
        tests = []
        test_classes = []
        test_funcs = []
        if not discovered or self.selector.wantModule(module):
            for item in dir(module):
                test = getattr(module, item, None)
                if isclass(test):
                    if self.selector.wantClass(test):
                        test_classes.append(test)
                elif isfunction(test) and self.selector.wantFunction(test):
                    test_funcs.append(test)

            test_classes = sort_list(test_classes, lambda x: x.__name__)
            tests.extend(self.makeTest(t, parent=module) for t in test_classes)

            test_funcs = sort_list(test_funcs, func_lineno)
            tests.extend(self.makeTest(t, parent=module) for t in test_funcs)

        module_paths = getattr(module, '__path__', [])

        if path:
            path = os.path.normcase(os.path.realpath(path))

        for module_path in module_paths:
            log.debug("Load tests from module path %s?", module_path)
            log.debug("path: %s os.path.realpath(%s): %s",
                      path, os.path.normcase(module_path),
                      os.path.realpath(os.path.normcase(module_path)))
            if (self.config.traverseNamespace or not path) or                     os.path.realpath(
                        os.path.normcase(module_path)).startswith(path):
                if os.path.isdir(module_path):
                    tests.extend(self.loadTestsFromDir(module_path))

        for test in self.config.plugins.loadTestsFromModule(module, path):
            tests.append(test)

        return self.suiteClass(ContextList(tests, context=module))

    def loadTestsFromName(self, name, module=None, discovered=False):
        """Load tests from the entity with the given name.

        The name may indicate a file, directory, module, or any object
        within a module. See `nose.util.split_test_name` for details on
        test name parsing.
        """
        log.debug("load from %s (%s)", name, module)

        suite = self.suiteClass

        plug_tests = self.config.plugins.loadTestsFromName(name, module)
        if plug_tests:
            return suite(plug_tests)

        addr = TestAddress(name, workingDir=self.workingDir)
        if module:
            if addr.call:
                name = addr.call
            parent, obj = self.resolve(name, module)
            if (isclass(parent)
                    and getattr(parent, '__module__', None) != module.__name__
                    and not isinstance(obj, Failure)):
                parent = transplant_class(parent, module.__name__)
                obj = getattr(parent, obj.__name__)
            log.debug("parent %s obj %s module %s", parent, obj, module)
            if isinstance(obj, Failure):
                return suite([obj])
            return suite(
                ContextList([self.makeTest(obj, parent)], context=parent)
            )

        if addr.module:
            try:
                if addr.filename is None:
                    module = resolve_name(addr.module)
                else:
                    self.config.plugins.beforeImport(
                        addr.filename, addr.module)
                    try:
                        module = self.importer.importFromPath(
                            addr.filename, addr.module)
                    finally:
                        self.config.plugins.afterImport(
                            addr.filename, addr.module)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                exc = sys.exc_info()
                return suite([Failure(
                    exc[0], exc[1], exc[2],
                    address=addr.totuple()
                )])

            if addr.call:
                return self.loadTestsFromName(addr.call, module)
            return self.loadTestsFromModule(
                module, addr.filename, discovered=discovered
            )

        if addr.filename:
            path = addr.filename
            if addr.call:
                package = getpackage(path)
                if package is None:
                    return suite([
                        Failure(
                            ValueError,
                            "Can't find callable %s in file %s: "
                            "file is not a python module" % (addr.call, path),
                            address=addr.totuple(),
                        )
                    ])
                return self.loadTestsFromName(addr.call, module=package)

            if op_isdir(path):
                return LazySuite(
                    lambda: self.loadTestsFromDir(path)
                )
            if op_isfile(path):
                return self.loadTestsFromFile(path)
            return suite([
                Failure(
                    OSError,
                    "No such file %s" % path,
                    address=addr.totuple(),
                )
            ])

        return suite([
            Failure(
                ValueError,
                "Unresolvable test name %s" % name,
                address=addr.totuple(),
            )
        ])

    def loadTestsFromNames(self, names, module=None):
        """Load tests from all names, returning a suite containing all
        tests.
        """
        plug_res = self.config.plugins.loadTestsFromNames(names, module)
        if plug_res:
            suite, names = plug_res
            if suite:
                return self.suiteClass([
                    self.suiteClass(suite),
                    unittest.TestLoader.loadTestsFromNames(self, names, module)
                ])
        return unittest.TestLoader.loadTestsFromNames(self, names, module)

    def loadTestsFromTestCase(self, testCaseClass):
        """Load tests from a unittest.TestCase subclass.
        """
        cases = []
        plugins = self.config.plugins
        for case in plugins.loadTestsFromTestCase(testCaseClass):
            cases.append(case)
        if not cases:
            return super().loadTestsFromTestCase(testCaseClass)
        cases.extend([
            case for case in super().loadTestsFromTestCase(testCaseClass)
        ])
        return self.suiteClass(cases)

    def loadTestsFromTestClass(self, cls):
        """Load tests from a test class that is *not* a unittest.TestCase
        subclass.

        In this case, we can't depend on the class's `__init__` taking method
        name arguments, so we have to compose a MethodTestCase for each
        method in the class that looks testlike.
        """

        def wanted(attr, cls=cls, sel=self.selector):
            item = getattr(cls, attr, None)
            if isfunction(item):
                item = unbound_method(cls, item)
            elif not ismethod(item):
                return False
            return sel.wantMethod(item)

        cases = [
            self.makeTest(getattr(cls, case), cls)
            for case in filter(wanted, dir(cls))
        ]
        for test in self.config.plugins.loadTestsFromTestClass(cls):
            cases.append(test)
        return self.suiteClass(ContextList(cases, context=cls))

    def makeTest(self, obj, parent=None):
        try:
            return self._makeTest(obj, parent)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            exc = sys.exc_info()
            try:
                addr = test_address(obj)
            except KeyboardInterrupt:
                raise
            except Exception:
                addr = None
            return Failure(exc[0], exc[1], exc[2], address=addr)

    def _makeTest(self, obj, parent=None):
        """Given a test object and its parent, return a test case
        or test suite.
        """
        plug_tests = []
        try:
            addr = test_address(obj)
        except KeyboardInterrupt:
            raise
        except Exception:
            addr = None
        for test in self.config.plugins.makeTest(obj, parent):
            plug_tests.append(test)
        try:
            if plug_tests:
                return self.suiteClass(plug_tests)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            exc = sys.exc_info()
            return Failure(exc[0], exc[1], exc[2], address=addr)

        if isfunction(obj) and parent and not isinstance(parent, types.ModuleType):
            obj = unbound_method(parent, obj)

        if isinstance(obj, unittest.TestCase):
            return obj

        if isclass(obj):
            if parent and obj.__module__ != parent.__name__:
                obj = transplant_class(obj, parent.__name__)
            if issubclass(obj, unittest.TestCase):
                return self.loadTestsFromTestCase(obj)
            return self.loadTestsFromTestClass(obj)

        if ismethod(obj):
            if parent is None:
                parent = obj.__class__
            if issubclass(parent, unittest.TestCase):
                return parent(obj.__name__)
            if isgenerator(obj):
                return self.loadTestsFromGeneratorMethod(obj, parent)
            return MethodTestCase(obj)

        if isfunction(obj):
            if parent and obj.__module__ != parent.__name__:
                obj = transplant_func(obj, parent.__name__)
            if isgenerator(obj):
                return self.loadTestsFromGenerator(obj, parent)
            return FunctionTestCase(obj)

        return Failure(
            TypeError,
            "Can't make a test from %s" % obj,
            address=addr,
        )

    def resolve(self, name, module):
        """Resolve name within module
        """
        obj = module
        parts = name.split('.')
        for part in parts:
            parent, obj = obj, getattr(obj, part, None)
        if obj is None:
            obj = Failure(ValueError, "No such test %s" % name)
        return parent, obj

    def parseGeneratedTest(self, test):
        """Given the yield value of a test generator, return a func and args.

        This is used in the two loadTestsFromGenerator* methods.

        """
        if not isinstance(test, tuple):
            test_func, arg = test, tuple()
        elif len(test) == 1:
            test_func, arg = test[0], tuple()
        else:
            test_func, arg = test[0], test[1:]
        return test_func, arg


defaultTestLoader = TestLoader

"""
Regression test suite for nose-py3
"""


import cProfile
import os
import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path

from nose import case, proxy
from nose.suite import ContextList, ContextSuite, ContextSuiteFactory, LazySuite
from nose.config import Config
import nose.failure
from nose.plugins import PluginTester
from nose.plugins.attrib import AttributeSelector
from nose.plugins.deprecated import Deprecated, DeprecatedTest
from nose.plugins.skip import Skip, SkipTest
from nose.pyversion import cmp_to_key, isgenerator, sort_list, unbound_method
from nose.result import NoseTextTestResult, TextTestResult
from nose.selector import Selector
from nose.util import (
    absdir,
    absfile,
    anyp,
    file_like,
    func_lineno,
    getfilename,
    getpackage,
    is_generator,
    isclass,
    is_executable,
    ispackage,
    isproperty,
    ln,
    ls_tree,
    odict,
    regex_last_key,
    resolve_name,
    safe_str,
    split_test_name,
    src,
    test_address,
    tolist,
    transplant_class,
    transplant_func,
    try_run,
)
from nose.tools import (
    TimeExpired,
    eq_,
    istest,
    make_decorator,
    nottest,
    ok_,
    raises,
    timed,
    with_setup,
)
import nose.tools


class TestUtilFileAndPathHelpers(unittest.TestCase):
    def test_file_like_returns_actual_bool(self):
        for value in (
            "foo",
            "foo.py",
            "foo/bar",
            "foo-bar",
            "",
            "foo.pyc",
        ):
            self.assertIs(type(file_like(value)), bool)

    def test_file_like_module_name(self):
        self.assertFalse(file_like("some_module_name"))
        self.assertFalse(file_like("nose.util"))

    def test_file_like_python_file(self):
        self.assertTrue(file_like("test_example.py"))
        self.assertTrue(file_like("./test_example.py"))
        self.assertTrue(file_like("pkg/test_example.py"))

    def test_file_like_path(self):
        self.assertTrue(file_like("pkg/test_example"))

    def test_file_like_invalid_identifier(self):
        self.assertTrue(file_like("foo-bar"))
        self.assertTrue(file_like("123foo"))

    def test_file_like_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "plain_name")
            Path(path).write_text("x", encoding="utf-8")
            self.assertTrue(file_like(path))

    def test_absdir(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(absdir(directory), os.path.abspath(directory))
            self.assertIsNone(absdir(os.path.join(directory, "missing")))

    def test_absfile_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "example.py")
            Path(path).write_text("", encoding="utf-8")
            self.assertEqual(absfile(path), os.path.abspath(path))

    def test_absfile_directory_package_returns_init(self):
        with tempfile.TemporaryDirectory() as directory:
            package = os.path.join(directory, "pkg")
            os.mkdir(package)
            init = os.path.join(package, "__init__.py")
            Path(init).write_text("", encoding="utf-8")
            self.assertEqual(absfile(package), init)

    def test_absfile_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(absfile("missing.py", directory))

    def test_absfile_searches_sequence(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            path = os.path.join(second, "example.py")
            Path(path).write_text("", encoding="utf-8")
            self.assertEqual(
                absfile("example.py", [first, second]),
                os.path.abspath(path),
            )

    def test_anyp(self):
        self.assertTrue(anyp(lambda value: value == 2, [1, 2, 3]))
        self.assertFalse(anyp(lambda value: value == 9, [1, 2, 3]))

    def test_tolist(self):
        self.assertEqual(tolist("foo"), ["foo"])
        self.assertEqual(tolist(["foo", "bar"]), ["foo", "bar"])
        self.assertEqual(tolist("foo,bar"), ["foo", "bar"])
        self.assertEqual(tolist("separate,values, with, commas,  spaces , are    ,ok"),
                         ["separate", "values", "with", "commas", "spaces", "are", "ok"])
        self.assertEqual(tolist(".*foo/.*,.1"), [".*foo/.*", ".1"])
        self.assertIsNone(tolist(None))

    def test_ls_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "file1.py").write_text("", encoding="utf-8")
            os.mkdir(os.path.join(directory, "subdir"))
            Path(directory, "subdir", "file2.py").write_text("", encoding="utf-8")
            tree = ls_tree(directory)
            self.assertIn("file1.py", tree)
            self.assertIn("subdir", tree)
            self.assertIn("file2.py", tree)


class TestFuncAndPackageHelpers(unittest.TestCase):
    def test_func_lineno_normal_function(self):
        def example():
            pass

        self.assertEqual(func_lineno(example), example.__code__.co_firstlineno)

    def test_func_lineno_compat_attribute_wins(self):
        def example():
            pass

        example.compat_co_firstlineno = 123
        self.assertEqual(func_lineno(example), 123)

    def test_func_lineno_missing_code(self):
        class CallableWithoutCode:
            def __call__(self):
                pass

        self.assertEqual(func_lineno(CallableWithoutCode()), -1)

    def test_func_lineno_result_is_int(self):
        def example():
            pass

        self.assertIs(type(func_lineno(example)), int)

    def test_src_none(self):
        self.assertIsNone(src(None))

    def test_src_py(self):
        self.assertEqual(src("example.py"), "example.py")

    def test_src_pyc(self):
        self.assertEqual(src("example.pyc"), "example.py")

    def test_src_pyo(self):
        self.assertEqual(src("example.pyo"), "example.py")

    def test_src_other_extension(self):
        self.assertEqual(src("example.txt"), "example.txt")

    def test_getpackage_files_and_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            old_cwd = os.getcwd()
            os.chdir(directory)
            try:
                Path("foo.py").write_text("", encoding="utf-8")
                os.mkdir("nose")
                Path("nose/__init__.py").write_text("", encoding="utf-8")
                os.mkdir("nose/plugins")
                Path("nose/plugins/__init__.py").write_text("", encoding="utf-8")
                Path("nose/util.py").write_text("", encoding="utf-8")

                self.assertEqual(getpackage("foo.py"), "foo")
                self.assertEqual(getpackage("nose/util.py"), "nose.util")
                self.assertEqual(getpackage("nose"), "nose")
                self.assertEqual(getpackage("nose/plugins"), "nose.plugins")
                self.assertEqual(
                    getpackage("nose/plugins/__init__.py"),
                    "nose.plugins",
                )
            finally:
                os.chdir(old_cwd)

    def test_getpackage_absolute_path(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "pkg"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            self.assertEqual(getpackage(str(package)), "pkg")

    def test_getpackage_non_python_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.txt"
            path.write_text("", encoding="utf-8")
            self.assertIsNone(getpackage(str(path)))

    def test_ispackage(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "pkg"
            package.mkdir()
            self.assertFalse(ispackage(str(package)))
            (package / "__init__.py").write_text("", encoding="utf-8")
            self.assertTrue(ispackage(str(package)))

    def test_ispackage_requires_identifier(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "not-a-package"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            self.assertFalse(ispackage(str(package)))

    def test_isclass(self):
        class Example:
            pass

        self.assertTrue(isclass(Example))
        self.assertTrue(isclass(type))
        self.assertFalse(isclass(Example()))

    def test_isproperty(self):
        class Example:
            @property
            def value(self):
                return 1

        self.assertTrue(isproperty(Example.value))
        self.assertFalse(isproperty(Example().value))

    def test_getfilename_module(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "example.py").write_text("", encoding="utf-8")
            self.assertEqual(
                getfilename("example", directory),
                os.path.join(directory, "example.py"),
            )

    def test_getfilename_package(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "pkg"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            self.assertEqual(getfilename("pkg", directory), str(package))

    def test_ln(self):
        self.assertEqual(
            ln("hello there"),
            "---------------------------- hello there -----------------------------",
        )


class TestResolveAndSplitNames(unittest.TestCase):
    def test_resolve_name_module(self):
        self.assertIs(resolve_name("nose.util"), sys.modules["nose.util"])

    def test_resolve_name_attribute(self):
        self.assertIs(resolve_name("nose.util.resolve_name"), resolve_name)

    def test_resolve_name_explicit_module(self):
        self.assertIs(
            resolve_name("resolve_name", sys.modules["nose.util"]),
            resolve_name,
        )

    def test_split_test_name_module(self):
        self.assertEqual(split_test_name("nose.util"), (None, "nose.util", None))

    def test_split_test_name_file(self):
        self.assertEqual(
            split_test_name("foo.py"),
            (os.path.normpath("foo.py"), None, None),
        )

    def test_split_test_name_module_callable(self):
        self.assertEqual(
            split_test_name("nose.util:resolve_name"),
            (None, "nose.util", "resolve_name"),
        )

    def test_split_test_name_file_callable(self):
        self.assertEqual(
            split_test_name("tests/test_util.py:test_file_like"),
            (os.path.normpath("tests/test_util.py"), None, "test_file_like"),
        )

    def test_split_test_name_colon_prefix(self):
        self.assertEqual(split_test_name(":Baz"), (None, None, "Baz"))

    def test_split_test_name_colon_in_file(self):
        self.assertEqual(
            split_test_name("foo:bar/baz.py"),
            (os.path.normpath("foo:bar/baz.py"), None, None),
        )

    def test_split_test_name_windows_paths(self):
        np = os.path.normpath
        self.assertEqual(split_test_name(r"c:\some\path.py:a_test"),
                         (np(r"c:\some\path.py"), None, "a_test"))
        self.assertEqual(split_test_name(r"c:\some\path.py"),
                         (np(r"c:\some\path.py"), None, None))
        self.assertEqual(split_test_name(r"c:/some/other/path.py"),
                         (np(r"c:/some/other/path.py"), None, None))
        self.assertEqual(split_test_name(r"c:/some/other/path.py:Class.test"),
                         (np(r"c:/some/other/path.py"), None, "Class.test"))

    def test_split_test_name_invalid_multiple_colons(self):
        with self.assertRaises(ValueError):
            split_test_name("cat:dog:something")


class TestNoseTools(unittest.TestCase):
    def test_ok(self):
        ok_(True)
        with self.assertRaises(AssertionError) as cm:
            ok_(False, "custom failure message")
        self.assertEqual(str(cm.exception), "custom failure message")

    def test_eq(self):
        eq_(1, 1)
        with self.assertRaises(AssertionError) as cm:
            eq_(1, 0, "custom message")
        self.assertEqual(str(cm.exception), "custom message")

        with self.assertRaises(AssertionError) as cm:
            eq_(1, 0)
        self.assertEqual(str(cm.exception), "1 != 0")

    def test_eq_unittest_flag(self):
        self.assertIn("__unittest", eq_.__globals__)

    def test_istest_and_nottest(self):
        @nottest
        def helper():
            pass

        @istest
        def test_func():
            pass

        self.assertFalse(getattr(helper, "__test__", True))
        self.assertTrue(getattr(test_func, "__test__", False))
        self.assertNotIn("__unittest", istest.__globals__)

    def test_raises(self):
        @raises(TypeError)
        def raise_typeerror():
            raise TypeError("foo")

        @raises(ValueError)
        def raise_other_error():
            raise TypeError("foo")

        @raises(TypeError)
        def no_raise():
            pass

        raise_typeerror()
        with self.assertRaises(TypeError):
            raise_other_error()
        with self.assertRaises(AssertionError):
            no_raise()

    def test_timed(self):
        import time

        @timed(0.5)
        def quick():
            time.sleep(0.01)
            return 42

        @timed(0.01)
        def too_slow():
            time.sleep(0.05)

        self.assertEqual(quick(), 42)
        with self.assertRaises(TimeExpired):
            too_slow()

    def test_make_decorator(self):
        def original():
            pass
        original.setup = "setup_marker"
        original.teardown = "teardown_marker"

        def wrapper():
            pass

        decorated = make_decorator(original)(wrapper)
        self.assertEqual(decorated.setup, "setup_marker")
        self.assertEqual(decorated.teardown, "teardown_marker")

    def test_multiple_with_setup(self):
        called = []

        def test():
            called.append("test")

        def s1():
            called.append("s1")

        def t1():
            called.append("t1")

        def s2():
            called.append("s2")

        def t2():
            called.append("t2")

        wrapped = with_setup(s2, t2)(test)
        wrapped = with_setup(s1, t1)(wrapped)
        test_case = case.FunctionTestCase(wrapped)
        res = unittest.TestResult()
        test_case.run(res)
        self.assertEqual(called, ["s1", "s2", "test", "t2", "t1"])


class TestTestAddress(unittest.TestCase):
    def test_module_address(self):
        module = sys.modules[__name__]
        result = test_address(module)
        self.assertEqual(result[1], __name__)

    def test_function_address(self):
        def example():
            pass

        module_name = __name__
        old_module = example.__module__
        example.__module__ = module_name
        try:
            result = test_address(example)
            self.assertEqual(result[1], module_name)
            self.assertEqual(result[2], "example")
        finally:
            example.__module__ = old_module

    def test_class_address(self):
        class Example:
            pass

        result = test_address(Example)
        self.assertEqual(result[1], __name__)
        self.assertEqual(result[2], "Example")

    def test_method_address(self):
        class Example:
            def test_method(self):
                pass

        result = test_address(Example().test_method)
        self.assertEqual(result[1], __name__)
        self.assertEqual(result[2], "Example.test_method")

    def test_unittest_function_test_case_address(self):
        def example():
            pass

        test = unittest.FunctionTestCase(example)
        result = test_address(test)
        self.assertEqual(result[1], __name__)
        self.assertEqual(result[2], "example")

    def test_unittest_test_case_address(self):
        class Example(unittest.TestCase):
            def test_method(self):
                pass

        test = Example("test_method")
        result = test_address(test)
        self.assertEqual(result[1], __name__)
        self.assertEqual(result[2], "Example.test_method")

    def test_address_returns_declared_tuple_shape(self):
        def example():
            pass

        result = test_address(example)
        self.assertEqual(len(result), 3)


class TestTryRun(unittest.TestCase):
    def test_runs_first_available_fixture(self):
        calls = []

        class Example:
            def setup(self):
                calls.append("setup")

            def setUp(self):
                calls.append("setUp")

        obj = Example()
        result = try_run(obj, ("setup", "setUp"))
        self.assertIsNone(result)
        self.assertEqual(calls, ["setup"])

    def test_uses_second_fixture_when_first_absent(self):
        calls = []

        class Example:
            def setUp(self):
                calls.append("setUp")

        try_run(Example(), ("setup", "setUp"))
        self.assertEqual(calls, ["setUp"])

    def test_returns_when_no_fixture_exists(self):
        self.assertIsNone(try_run(object(), ("setup", "setUp")))

    def test_fixture_exception_propagates(self):
        class Example:
            def setup(self):
                raise RuntimeError("setup failed")

        with self.assertRaisesRegex(RuntimeError, "setup failed"):
            try_run(Example(), ("setup",))

    def test_module_fixture_without_argument(self):
        module = types.ModuleType("fixture_module")

        def setup():
            module.called = True

        module.setup = setup
        try_run(module, ("setup",))
        self.assertTrue(module.called)

    def test_module_fixture_with_module_argument(self):
        module = types.ModuleType("fixture_module")

        def setup(received):
            module.received = received

        module.setup = setup
        try_run(module, ("setup",))
        self.assertIs(module.received, module)

    def test_callable_object_module_fixture(self):
        module = types.ModuleType("fixture_module")

        class Fixture:
            def __init__(self):
                self.received = None

            def __call__(self, received):
                self.received = received

        fixture = Fixture()
        module.setup = fixture
        try_run(module, ("setup",))
        self.assertIs(fixture.received, module)

    def test_noncallable_module_fixture_raises_type_error(self):
        module = types.ModuleType("fixture_module")
        module.setup = object()

        with self.assertRaises(TypeError):
            try_run(module, ("setup",))


class TestCaseWrappers(unittest.TestCase):
    def test_function_test_case_runs_test(self):
        calls = []

        def test():
            calls.append("test")

        FunctionTestCase = case.FunctionTestCase
        test_case = FunctionTestCase(test)
        result = unittest.TestResult()
        test_case.run(result)

        self.assertEqual(calls, ["test"])
        self.assertTrue(result.wasSuccessful())

    def test_function_test_case_explicit_setup(self):
        calls = []

        def setup():
            calls.append("setup")

        def test():
            calls.append("test")

        test_case = case.FunctionTestCase(test, setUp=setup)
        result = unittest.TestResult()
        test_case.run(result)

        self.assertEqual(calls, ["setup", "test"])

    def test_function_test_case_explicit_teardown(self):
        calls = []

        def teardown():
            calls.append("teardown")

        def test():
            calls.append("test")

        test_case = case.FunctionTestCase(test, tearDown=teardown)
        result = unittest.TestResult()
        test_case.run(result)

        self.assertEqual(calls, ["test", "teardown"])

    def test_function_test_case_setup_failure_prevents_test(self):
        calls = []

        def setup():
            calls.append("setup")
            raise RuntimeError("setup failed")

        def test():
            calls.append("test")

        test_case = case.FunctionTestCase(test, setUp=setup)
        result = unittest.TestResult()
        test_case.run(result)

        self.assertEqual(calls, ["setup"])
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.failures), 0)

    def test_function_test_case_test_failure(self):
        def test():
            raise AssertionError("boom")

        test_case = case.FunctionTestCase(test)
        result = unittest.TestResult()
        test_case.run(result)

        self.assertEqual(len(result.failures), 1)
        self.assertEqual(len(result.errors), 0)

    def test_function_test_case_test_error(self):
        def test():
            raise TypeError("boom")

        test_case = case.FunctionTestCase(test)
        result = unittest.TestResult()
        test_case.run(result)

        self.assertEqual(len(result.errors), 1)

    def test_function_test_case_generator_argument(self):
        received = []

        def test(value):
            received.append(value)

        test_case = case.FunctionTestCase(test, arg=(42,))
        result = unittest.TestResult()
        test_case.run(result)

        self.assertEqual(received, [42])

    def test_function_test_case_address(self):
        def test():
            pass

        test_case = case.FunctionTestCase(test)
        address = test_case.address()
        self.assertEqual(address[2], "test")

    def test_function_test_case_string(self):
        def test():
            pass

        test_case = case.FunctionTestCase(test)
        self.assertIn("test", str(test_case))

    def test_method_test_case_runs_bound_method(self):
        calls = []

        class Example:
            def test(self):
                calls.append("test")

        method = Example().test
        test_case = case.MethodTestCase(method)
        result = unittest.TestResult()
        test_case.run(result)

        self.assertEqual(calls, ["test"])
        self.assertTrue(result.wasSuccessful())

    def test_method_test_case_setup_and_teardown(self):
        calls = []

        class Example:
            def setUp(self):
                calls.append("setup")

            def tearDown(self):
                calls.append("teardown")

            def test(self):
                calls.append("test")

        test_case = case.MethodTestCase(Example().test)
        result = unittest.TestResult()
        test_case.run(result)

        self.assertEqual(calls, ["setup", "test", "teardown"])

    def test_method_test_case_setup_failure_prevents_test(self):
        calls = []

        class Example:
            def setUp(self):
                calls.append("setup")
                raise RuntimeError("setup failed")

            def test(self):
                calls.append("test")

        test_case = case.MethodTestCase(Example().test)
        result = unittest.TestResult()
        test_case.run(result)

        self.assertEqual(calls, ["setup"])
        self.assertEqual(len(result.errors), 1)

    def test_test_wrapper_calls_wrapped_test(self):
        calls = []

        def test(result):
            calls.append(result)

        wrapped = case.Test(test)
        result = unittest.TestResult()
        wrapped.run(result)

        self.assertEqual(calls, [result])

    def test_test_wrapper_error_is_recorded(self):
        def test(result):
            raise TypeError("oops, wrong type")

        wrapped = case.Test(test)
        result = unittest.TestResult()
        wrapped.run(result)

        self.assertEqual(len(result.errors), 1)

    def test_test_wrapper_keyboard_interrupt_propagates(self):
        def test(result):
            raise KeyboardInterrupt()

        wrapped = case.Test(test)
        result = unittest.TestResult()

        with self.assertRaises(KeyboardInterrupt):
            wrapped.run(result)

    def test_test_wrapper_plugin_prepare_test_case(self):
        calls = []

        def original(result):
            calls.append("original")

        def prepared(result):
            calls.append("prepared")

        class Plugins:
            def prepareTestCase(self, test_case):
                return prepared

            def testName(self, test_case):
                return None

            def describeTest(self, test_case):
                return None

        config = Config()
        config.plugins = Plugins()
        wrapped = case.Test(original, config=config)
        result = unittest.TestResult()
        wrapped.run(result)

        self.assertEqual(calls, ["prepared"])


class TestTestBase(unittest.TestCase):
    def test_id(self):
        def test():
            pass

        test_case = case.FunctionTestCase(test)
        self.assertEqual(test_case.id(), str(test_case))

    def test_short_description_from_description(self):
        def test():
            pass

        test.description = "explicit description"
        test_case = case.FunctionTestCase(test)
        self.assertEqual(test_case.shortDescription(), "explicit description")

    def test_short_description_from_docstring(self):
        def test():
            """first line
            second line
            """
            pass

        test_case = case.FunctionTestCase(test)
        self.assertEqual(test_case.shortDescription(), "first line")


class TestOdDictCompatibility(unittest.TestCase):
    def test_preserves_insertion_order(self):
        value = odict()
        value["one"] = 1
        value["two"] = 2
        self.assertEqual(value.keys(), ["one", "two"])
        self.assertEqual(list(value.items()), [("one", 1), ("two", 2)])

    def test_reassignment_does_not_duplicate_key(self):
        value = odict()
        value["one"] = 1
        value["one"] = 2
        self.assertEqual(value.keys(), ["one"])

    def test_delete(self):
        value = odict()
        value["one"] = 1
        del value["one"]
        self.assertEqual(value.keys(), [])

    def test_clear(self):
        value = odict()
        value["one"] = 1
        value.clear()
        self.assertEqual(value.keys(), [])

    def test_copy(self):
        value = odict()
        value["one"] = 1
        copied = value.copy()
        self.assertEqual(copied.keys(), ["one"])
        self.assertIsNot(copied, value)

    def test_setdefault(self):
        value = odict()
        self.assertEqual(value.setdefault("one", 1), 1)
        self.assertEqual(value.keys(), ["one"])
        self.assertEqual(value.setdefault("one", 2), 1)
        self.assertEqual(value.keys(), ["one"])

    def test_update(self):
        value = odict()
        value.update({"one": 1, "two": 2})
        self.assertEqual(value.keys(), ["one", "two"])

    def test_string_representation(self):
        value = odict()
        value["one"] = 1
        self.assertEqual(str(value), "{'one': 1}")


class TestStringAndMiscHelpers(unittest.TestCase):
    def test_safe_str_string(self):
        self.assertEqual(safe_str("hello"), "hello")

    def test_safe_str_bytes(self):
        self.assertEqual(safe_str(b"hello"), "hello")

    def test_safe_str_invalid_bytes(self):
        self.assertEqual(safe_str(b"\xff"), "\ufffd")

    def test_safe_str_exception(self):
        self.assertEqual(safe_str(ValueError("one", "two")), "one two")

    def test_is_executable_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(is_executable(os.path.join(directory, "missing")))

    def test_is_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "executable")
            Path(path).write_text("", encoding="utf-8")
            mode = os.stat(path).st_mode
            os.chmod(path, mode | stat.S_IXUSR)
            self.assertTrue(is_executable(path))

    def test_regex_last_key(self):
        regex = __import__("re").compile(r"test")
        key = regex_last_key(regex)
        self.assertEqual(key("test"), (1, "test"))
        self.assertEqual(key("example"), (0, "example"))

    def test_is_generator_alias(self):
        self.assertIs(is_generator, __import__("nose.pyversion", fromlist=["isgenerator"]).isgenerator)


class TestTransplantHelpers(unittest.TestCase):
    def test_transplant_func_non_generator(self):
        def original(value):
            """original doc"""
            return value + 1

        transplanted = transplant_func(original, "fake_module")
        self.assertEqual(transplanted(1), 2)
        self.assertEqual(transplanted.__module__, "fake_module")
        self.assertEqual(transplanted.__name__, original.__name__)

    def test_transplant_func_generator(self):
        def original():
            yield 1
            yield 2

        transplanted = transplant_func(original, "fake_module")
        self.assertEqual(list(transplanted()), [1, 2])
        self.assertEqual(transplanted.__module__, "fake_module")

    def test_transplant_class(self):
        class Original:
            pass

        transplanted = transplant_class(Original, "fake_module")
        self.assertEqual(transplanted.__name__, "Original")
        self.assertEqual(transplanted.__qualname__, "Original")
        self.assertEqual(transplanted.__module__, "fake_module")
        self.assertTrue(issubclass(transplanted, Original))


class TestProfilerAndCallableContract(unittest.TestCase):
    def test_cprofile_runcall_accepts_result_argument(self):
        calls = []

        def test(result):
            calls.append(result)

        result = object()
        profiler = cProfile.Profile()
        profiler.runcall(test, result)

        self.assertEqual(calls, [result])

    def test_nested_profiler_style_closure(self):
        calls = []

        def test(result):
            calls.append(result)

        profiler = cProfile.Profile()

        def run_and_profile(result, prof=profiler, test=test):
            prof.runcall(test, result)

        result = object()
        run_and_profile(result)

        self.assertEqual(calls, [result])


class TestUnicodeAndResultHandling(unittest.TestCase):
    def test_unicode_exception_is_recorded(self):
        def test():
            raise Exception("日本")

        test_case = case.FunctionTestCase(test)
        result = unittest.TestResult()
        test_case.run(result)

        self.assertEqual(len(result.errors), 1)
        self.assertIn("日本", result.errors[0][1])


    def test_real_unittest_failure_remains_failure(self):
        class Example(unittest.TestCase):
            def runTest(self):
                self.assertEqual("this", "that")

        result = unittest.TestResult()
        Example().run(result)

        self.assertEqual(len(result.failures), 1)
        self.assertEqual(len(result.errors), 0)


class TestPyversion(unittest.TestCase):
    def test_unbound_method(self):
        class Dummy:
            def method(self):
                return "hello"

        unbound = unbound_method(Dummy, Dummy.method)
        inst = Dummy()
        self.assertEqual(unbound(inst), "hello")

    def test_sort_list(self):
        items = ["b", "a", "c"]
        sorted_items = sort_list(items, key=lambda x: x)
        self.assertEqual(sorted_items, ["a", "b", "c"])

    def test_cmp_to_key(self):
        def my_cmp(a, b):
            if a < b:
                return -1
            if a > b:
                return 1
            return 0

        key_fn = cmp_to_key(my_cmp)
        items = [3, 1, 2]
        items.sort(key=key_fn)
        self.assertEqual(items, [1, 2, 3])


class TestConfig(unittest.TestCase):
    def test_config_defaults(self):
        config = Config()
        self.assertTrue(config.testMatch.search("test_foo"))
        self.assertTrue(config.testMatch.search("foo_test"))
        self.assertFalse(config.testMatch.search("foo_bar"))
        self.assertEqual(config.verbosity, 1)

    def test_config_configure_env(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env = {"NOSE_VERBOSE": "3", "NOSE_WHERE": temp_dir}
            config = Config(env=env)
            config.configure(argv=["nosetests"])
            self.assertEqual(config.verbosity, 3)
            self.assertEqual(os.path.realpath(temp_dir), os.path.realpath(config.workingDir))


class TestSelector(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.selector = Selector(self.config)

    def test_want_function(self):
        def test_something():
            pass

        def helper():
            pass

        self.assertTrue(self.selector.wantFunction(test_something))
        self.assertFalse(self.selector.wantFunction(helper))

    def test_want_class(self):
        class TestClass:
            pass

        class HelperClass:
            pass

        self.assertTrue(self.selector.wantClass(TestClass))
        self.assertFalse(self.selector.wantClass(HelperClass))

    def test_want_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            pkg_dir = os.path.join(directory, "tests")
            os.mkdir(pkg_dir)
            self.assertTrue(self.selector.wantDirectory(pkg_dir))

            hidden_dir = os.path.join(directory, ".git")
            os.mkdir(hidden_dir)
            self.assertFalse(self.selector.wantDirectory(hidden_dir))

    def test_want_file(self):
        self.assertTrue(self.selector.wantFile("test_example.py"))
        self.assertFalse(self.selector.wantFile("example.pyc"))


class TestResultAndFailureTests(unittest.TestCase):
    def test_failure_case(self):
        try:
            raise ValueError("custom failure error")
        except ValueError:
            exc = sys.exc_info()

        fail_case = nose.failure.Failure(exc[0], exc[1], exc[2])
        res = unittest.TestResult()
        fail_case.run(res)

        self.assertEqual(len(res.errors), 1)
        self.assertIn("custom failure error", res.errors[0][1])

    def test_text_test_result_error_classes(self):
        import io
        stream = io.StringIO()
        config = Config()
        result = NoseTextTestResult(stream=stream, descriptions=True, verbosity=1, config=config)

        class SpecialError(Exception):
            pass

        result.errorClasses[SpecialError] = ([], "SPECIAL", True)

        class DummyTest(unittest.TestCase):
            def runTest(self):
                pass

        test = DummyTest()
        try:
            raise SpecialError("special error message")
        except SpecialError:
            err = sys.exc_info()

        result.addError(test, err)
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.errorClasses[SpecialError][0]), 1)


class TestLazySuite(unittest.TestCase):

    def setUp(self):
        class TC(unittest.TestCase):
            def test_one(self):
                pass

            def test_two(self):
                pass

        self.TC = TC

    def test_test_generator(self):
        TC = self.TC
        tests = [TC("test_one"), TC("test_two")]

        def gen_tests():
            for test in tests:
                yield test

        suite = LazySuite(gen_tests)
        self.assertEqual(list([test for test in suite]), tests)

    def test_lazy_and_nonlazy(self):
        TC = self.TC
        tests = [TC("test_one"), TC("test_two")]

        def gen_tests():
            for test in tests:
                yield test

        nonlazy = LazySuite(tests)
        lazy = LazySuite(gen_tests)

        self.assertTrue(lazy)
        self.assertTrue(nonlazy)

        lazytests = []
        nonlazytests = []
        for t in lazy:
            lazytests.append(t)
        for t in nonlazy:
            nonlazytests.append(t)
        slazy = list(map(str, lazytests))
        snonlazy = list(map(str, nonlazytests))
        self.assertEqual(slazy, snonlazy)

    def test_lazy_nonzero(self):
        TC = self.TC
        tests = [TC("test_one"), TC("test_two")]

        def gen_tests():
            for test in tests:
                yield test

        lazy = LazySuite(gen_tests)
        self.assertTrue(lazy)

        count = 0
        for test in lazy:
            self.assertTrue(test)
            count += 1
        self.assertEqual(count, 2)
        self.assertTrue(lazy)

        def gen_tests_empty():
            for test in []:
                yield test

        empty = LazySuite(gen_tests_empty)
        self.assertFalse(empty)


class DummyResultProxy(proxy.ResultProxy):
    called = []

    def __init__(self, result, test):
        self.result = result
        self.test = test

    def afterTest(self, test):
        self.called.append(("afterTest", test))

    def beforeTest(self, test):
        self.called.append(("beforeTest", test))

    def startTest(self, test):
        self.called.append(("startTest", test))

    def stopTest(self, test):
        self.called.append(("stopTest", test))

    def addError(self, test, err):
        self.called.append(("addError", test, err))


class DummyResultProxyFactory:
    def __call__(self, result, test):
        return DummyResultProxy(result, test)


class TestContextSuite(unittest.TestCase):

    def setUp(self):
        class TC(unittest.TestCase):
            def test_one(self):
                pass

            def test_two(self):
                pass

        self.TC = TC

    def test_tests_are_wrapped(self):
        suite = ContextSuite([self.TC("test_one"), self.TC("test_two")])
        for test in suite:
            self.assertIsInstance(test.test, self.TC)

    def test_nested_context_suites(self):
        suite = ContextSuite([self.TC("test_one"), self.TC("test_two")])
        suite2 = ContextSuite(suite)
        suite3 = ContextSuite([suite2])

        tests = [t for t in suite3]
        self.assertIsInstance(tests[0], ContextSuite)
        tests = [t for t in tests[0]]
        self.assertIsInstance(tests[0], ContextSuite)
        tests = [t for t in tests[0]]
        cases = list(filter(lambda t: isinstance(t, case.Test), tests))
        self.assertTrue(cases)
        self.assertEqual(len(cases), len(tests))

    def test_context_fixtures_called(self):
        class P:
            was_setup = False
            was_torndown = False

            def setup(self):
                self.was_setup = True

            def teardown(self):
                self.was_torndown = True

        context = P()
        suite = ContextSuite(
            [self.TC("test_one"), self.TC("test_two")],
            context=context,
        )
        res = unittest.TestResult()
        suite(res)

        self.assertFalse(res.errors)
        self.assertFalse(res.failures)
        self.assertTrue(context.was_setup)
        self.assertTrue(context.was_torndown)

    def test_context_fixtures_setup_fails(self):
        class P:
            was_setup = False
            was_torndown = False

            def setup(self):
                self.was_setup = True
                assert False, "Setup failed"

            def teardown(self):
                self.was_torndown = True

        context = P()
        suite = ContextSuite(
            [self.TC("test_one"), self.TC("test_two")],
            context=context,
        )
        res = unittest.TestResult()
        suite(res)

        self.assertFalse(res.failures)
        self.assertTrue(res.errors)
        self.assertTrue(context.was_setup)
        self.assertFalse(context.was_torndown)
        self.assertEqual(res.testsRun, 0)

    def test_context_fixtures_no_tests_no_setup(self):
        class P:
            was_setup = False
            was_torndown = False

            def setup(self):
                self.was_setup = True

            def teardown(self):
                self.was_torndown = True

        context = P()
        suite = ContextSuite([], context=context)
        res = unittest.TestResult()
        suite(res)

        self.assertFalse(res.failures)
        self.assertFalse(res.errors)
        self.assertFalse(context.was_setup)
        self.assertFalse(context.was_torndown)
        self.assertEqual(res.testsRun, 0)

    def test_result_proxy_used(self):
        class TC(unittest.TestCase):
            def runTest(self):
                raise Exception("error")

        DummyResultProxy.called[:] = []
        res = unittest.TestResult()
        suite = ContextSuite([TC()], resultProxy=DummyResultProxyFactory())
        suite(res)
        calls = [c[0] for c in DummyResultProxy.called]
        self.assertIn("addError", calls)
        self.assertIn("beforeTest", calls)
        self.assertIn("startTest", calls)
        self.assertIn("stopTest", calls)
        self.assertIn("afterTest", calls)


class TestContextSuiteFactory(unittest.TestCase):

    def test_ancestry(self):
        top = types.ModuleType("top")
        top.bot = types.ModuleType("top.bot")
        top.bot.end = types.ModuleType("top.bot.end")

        sys.modules["top"] = top
        sys.modules["top.bot"] = top.bot
        sys.modules["top.bot.end"] = top.bot.end

        class P:
            pass

        top.bot.P = P
        P.__module__ = "top.bot"

        csf = ContextSuiteFactory()
        P_ancestors = list([a for a in csf.ancestry(P)])
        self.assertEqual(P_ancestors, [top.bot, top])

        end_ancestors = list([a for a in csf.ancestry(top.bot.end)])
        self.assertEqual(end_ancestors, [top.bot, top])

        bot_ancestors = list([a for a in csf.ancestry(top.bot)])
        self.assertEqual(bot_ancestors, [top])

        top_ancestors = list([a for a in csf.ancestry(top)])
        self.assertEqual(top_ancestors, [])


class TestNoseCases(unittest.TestCase):

    def test_function_test_case(self):
        res = unittest.TestResult()
        a = []

        def func(a=a):
            a.append(1)

        test_case = case.FunctionTestCase(func)
        test_case(res)
        self.assertEqual(a[0], 1)

    def test_method_test_case(self):
        res = unittest.TestResult()
        a = []

        class TestClass:
            def test_func(self, a=a):
                a.append(1)

        test_case = case.MethodTestCase(unbound_method(TestClass, TestClass.test_func))
        test_case(res)
        self.assertEqual(a[0], 1)

    def test_method_test_case_fixtures(self):
        res = unittest.TestResult()
        called = []

        class TestClass:
            def setup(self):
                called.append("setup")

            def teardown(self):
                called.append("teardown")

            def test_func(self):
                called.append("test")

        test_case = case.MethodTestCase(unbound_method(TestClass, TestClass.test_func))
        test_case(res)
        self.assertEqual(called, ["setup", "test", "teardown"])

    def test_function_test_case_fixtures(self):
        res = unittest.TestResult()
        called = {}

        def st():
            called["st"] = True

        def td():
            called["td"] = True

        def func_exc():
            called["func"] = True
            raise TypeError("An exception")

        func_exc = with_setup(st, td)(func_exc)
        test_case = case.FunctionTestCase(func_exc)
        test_case(res)
        self.assertIn("st", called)
        self.assertIn("func", called)
        self.assertIn("td", called)


class TestNoseTestWrapperExtra(unittest.TestCase):

    def test_short_description(self):
        class TC(unittest.TestCase):
            def test_a(self):
                """This is the description"""
                pass

        case_a = case.FunctionTestCase(TC("test_a").test_a)
        desc = case_a.shortDescription()
        self.assertTrue(desc and desc.endswith("This is the description"))

    def test_unrepresentable_short_description(self):
        class TC(unittest.TestCase):
            def __str__(self):
                raise ValueError("simulate some mistake in this code")

            def runTest(self):
                pass

        test_case = case.Test(TC())
        self.assertIsNone(test_case.shortDescription())


class TestSkipPlugin(unittest.TestCase):

    def test_api_present(self):
        sk = Skip()
        self.assertTrue(hasattr(sk, "addOptions"))
        self.assertTrue(hasattr(sk, "configure"))
        self.assertTrue(hasattr(sk, "prepareTestResult"))

    def test_patched_result_handles_skip(self):
        import io
        stream = io.StringIO()
        res = TextTestResult(stream, 0, 1)
        sk = Skip()
        sk.prepareTestResult(res)

        class TC(unittest.TestCase):
            def test(self):
                raise SkipTest("skip me")

        test = TC("test")
        test(res)
        self.assertTrue(res.skipped)


class TestDeprecatedPlugin(unittest.TestCase):

    def test_api_present(self):
        dep = Deprecated()
        self.assertTrue(hasattr(dep, "addOptions"))
        self.assertTrue(hasattr(dep, "configure"))
        self.assertTrue(hasattr(dep, "prepareTestResult"))

    def test_patched_result_handles_deprecated(self):
        import io
        stream = io.StringIO()
        res = TextTestResult(stream, 0, 1)
        dep = Deprecated()
        dep.prepareTestResult(res)

        class TC(unittest.TestCase):
            def test(self):
                raise DeprecatedTest("deprecated me")

        test = TC("test")
        test(res)
        self.assertTrue(res.deprecated)


class TestIssue006(unittest.TestCase):
    def test_load_nested_generator(self):
        from nose import loader

        def gen():
            yield lambda: None

        def outer():
            yield gen()

        l = loader.TestLoader()
        suite = l.loadTestsFromGenerator(outer, sys.modules[__name__])
        tests = list(suite)
        self.assertTrue(len(tests) > 0)


class TestIssue065(unittest.TestCase):
    def test_package_test_loading(self):
        from nose import loader
        l = loader.TestLoader()
        support = os.path.join(os.path.dirname(__file__), "..", "unit_tests", "support", "issue065")
        if os.path.exists(support):
            suite = l.loadTestsFromName(support)
            self.assertTrue(suite)


class TestErrorClassWithStringException(unittest.TestCase):
    def test_string_exception(self):
        from nose.plugins.skip import SkipTest
        e = SkipTest("a string exception")
        self.assertEqual(str(e), "a string exception")


class TestIssue135(unittest.TestCase):
    def test_issue135(self):
        from nose.util import safe_str
        self.assertEqual(safe_str(Exception("hello")), "hello")


class TestIssue230(unittest.TestCase):
    def test_generator_yield_value(self):
        def gen():
            yield lambda: None

        self.assertTrue(is_generator(gen))


class TestIssue786(unittest.TestCase):
    def test_generator_yield_in_class(self):
        class TestClass:
            def test_evens(self):
                yield lambda x: self.assertEqual(x % 2, 0), 2

        inst = TestClass()
        res = list(inst.test_evens())
        self.assertEqual(len(res), 1)


support_dir = os.path.join(os.path.dirname(__file__), "support")


class AttributePluginTester(PluginTester, unittest.TestCase):
    plugins = [AttributeSelector()]
    suitepath = os.path.join(support_dir, "att")
    activate = "-v"

    def runTest(self):
        pass


class TestSimpleAttribute(AttributePluginTester):
    args = ["-a", "a"]

    def verify(self):
        self.assertIn("test_attr.test_one ... ok", self.output)
        self.assertIn("test_attr.test_two ... ok", self.output)


class TestNotSimpleAttribute(AttributePluginTester):
    args = ["-a", "!a"]

    def verify(self):
        self.assertNotIn("test_attr.test_one ... ok", self.output)


class TestAttributeValue(AttributePluginTester):
    args = ["-a", "b=2"]

    def verify(self):
        self.assertIn("TestClass.test_class_two ... ok", self.output)


class TestAttributeArray(AttributePluginTester):
    args = ["-a", "d=2"]

    def verify(self):
        self.assertIn("test_attr.test_one ... ok", self.output)


class TestAttributeArrayAnd(AttributePluginTester):
    args = ["-a", "d=1,d=2"]

    def verify(self):
        self.assertIn("test_attr.test_one ... ok", self.output)


class TestAttributeArrayOr(AttributePluginTester):
    args = ["-a", "d=1", "-a", "d=2"]

    def verify(self):
        self.assertIn("test_attr.test_one ... ok", self.output)


class TestInheritance(AttributePluginTester):
    args = ["-a", "from_super"]

    def verify(self):
        self.assertIn("TestSubclass.test_method ... ok", self.output)


class TestStatic(AttributePluginTester):
    args = ["-a", "with_static"]
    suitepath = os.path.join(support_dir, "att", "test_attr.py:Static")

    def verify(self):
        self.assertIn("Static.test_with_static ... ok", self.output)


class TestClassAndMethodAttrs(AttributePluginTester):
    args = ["-a", "meth_attr=method,cls_attr=class"]

    def verify(self):
        self.assertIn("(test_attr.TestClassAndMethodAttrs) ... ok", self.output)


class TestTopLevelNotSelected(AttributePluginTester):
    suitepath = os.path.join(support_dir, "issue771")
    args = ["-a", "!a"]

    def verify(self):
        self.assertIn("test.test_b ... ok", self.output)


class TestStaticMethod(AttributePluginTester):
    suitepath = os.path.join(support_dir, "attrib-static")
    args = ["-a", "!slow"]

    def verify(self):
        self.assertIn("test.TestAttrib.test_static ... ok", self.output)


class TestTestCasePluginCalls(unittest.TestCase):

    def test_describe_test_called(self):
        from nose.plugins import Plugin as NosePlugin, PluginManager

        class Descrip(NosePlugin):
            counter = 0
            enabled = True

            def describeTest(self, test):
                return "test #%s" % id(test)

            def testName(self, test):
                self.counter += 1
                return "(%s) test" % self.counter

        class TC(unittest.TestCase):
            def test_one(self):
                pass

            def test_two(self):
                pass

        config = Config(plugins=PluginManager(plugins=[Descrip()]))

        c1 = case.Test(TC("test_one"), config=config)
        c2 = case.Test(TC("test_two"), config=config)

        self.assertEqual(str(c1), "(1) test")
        self.assertEqual(str(c2), "(2) test")
        self.assertTrue(c1.shortDescription().startswith("test #"))
        self.assertTrue(c2.shortDescription().startswith("test #"))


class TestCommands(unittest.TestCase):
    def test_commands_importable(self):
        try:
            from nose import commands
            self.assertTrue(hasattr(commands, "nosetests"))
        except ImportError:
            pass


class TestImporter(unittest.TestCase):
    def test_importer_basic(self):
        from nose.importer import Importer
        imp = Importer()
        mod = imp.importFromDir(os.path.dirname(__file__), "test_exhaustive_regression")
        self.assertTrue(mod)


class TestResultSummary(unittest.TestCase):
    def test_result_summary(self):
        res = unittest.TestResult()
        self.assertEqual(res.testsRun, 0)
        self.assertTrue(res.wasSuccessful())


class TestDoctestPluginRunner(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "dtt")

    def runTest(self):
        pass


class TestFailureDetailRunner(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "fdp")

    def runTest(self):
        pass


class TestSingleTestPassRunner(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "pass")

    def runTest(self):
        pass


class TestIssue408(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "issue408")

    def runTest(self):
        pass


class TestIssue649(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "issue649")

    def runTest(self):
        pass


class TestBuggyGeneratorsRunner(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "test_buggy_generators.py")

    def runTest(self):
        pass


class TestFdpRunner(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "fdp")

    def runTest(self):
        pass


class TestIssue269Runner(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "issue269")

    def runTest(self):
        pass


class TestIssue279Runner(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "issue279")

    def runTest(self):
        pass


class TestLtfnRunner(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "ltfn")

    def runTest(self):
        pass


class TestNamespacePkgRunner(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "namespace_pkg", "namespace_pkg")

    def runTest(self):
        pass


class TestTodoRunner(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "todo")

    def runTest(self):
        pass


class TestXunitAsSuiteRunner(PluginTester, unittest.TestCase):
    activate = "-v"
    plugins = []
    suitepath = os.path.join(support_dir, "xunit")

    def runTest(self):
        pass


class TestPython310Compatibility(unittest.TestCase):

    def test_runtime_uses_current_python(self):
        self.assertGreaterEqual(sys.version_info[:2], (3, 10))


if __name__ == "__main__":
    unittest.main()

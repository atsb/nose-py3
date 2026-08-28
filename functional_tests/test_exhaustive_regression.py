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

from nose import case
from nose.config import Config
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
    odict,
    regex_last_key,
    resolve_name,
    safe_str,
    split_test_name,
    src,
    test_address,
    transplant_class,
    transplant_func,
    try_run,
)


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
        self.assertFalse(file_like("nose"))
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
            ("foo.py", None, None),
        )

    def test_split_test_name_module_callable(self):
        self.assertEqual(
            split_test_name("nose.util:resolve_name"),
            (None, "nose.util", "resolve_name"),
        )

    def test_split_test_name_file_callable(self):
        self.assertEqual(
            split_test_name("tests/test_util.py:test_file_like"),
            ("tests/test_util.py", None, "test_file_like"),
        )

    def test_split_test_name_invalid_multiple_colons(self):
        with self.assertRaises(ValueError):
            split_test_name("foo:bar:baz")


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


class TestPython310Compatibility(unittest.TestCase):

    def test_runtime_uses_current_python(self):
        self.assertGreaterEqual(sys.version_info[:2], (3, 10))


if __name__ == "__main__":
    unittest.main()

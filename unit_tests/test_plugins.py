import os
import sys
import tempfile
import unittest
from optparse import OptionParser

from nose import SkipTest
from nose.config import Config
from nose.plugins.attrib import AttributeSelector
from nose.plugins.base import Plugin
from nose.plugins.doctests import Doctest
from nose.plugins.failuredetail import FailureDetail
from nose.plugins.prof import Profile


class Bucket:
    """Minimal option container used by these plugin tests."""


class MockOptParser:
    """Minimal option-parser test double used by plugin option tests."""

    def __init__(self):
        self.opts = []

    def add_option(self, *args, **kwargs):
        self.opts.append((args, kwargs))


class P(Plugin):
    """Plugin of destiny!"""


class ErrPlugin:
    def load(self):
        raise Exception("Failed to load the plugin")


class ErrPkgResources:
    def iter_entry_points(self, ep):
        yield ErrPlugin()


class TestBuiltinPlugins(unittest.TestCase):
    def setUp(self):
        self.p = sys.path[:]

    def tearDown(self):
        sys.path = self.p[:]

    def test_add_options(self):
        conf = Config()
        opt = Bucket()
        parser = MockOptParser()
        plug = P()

        plug.add_options(parser)
        o, d = parser.opts[0]
        self.assertEqual(o[0], "--with-p")
        self.assertEqual(d["action"], "store_true")
        self.assertFalse(d["default"])
        self.assertEqual(d["dest"], "enable_plugin_p")
        self.assertEqual(
            d["help"],
            "Enable plugin P: Plugin of destiny! [NOSE_WITH_P]",
        )

        opt.enable_plugin_p = True
        plug.configure(opt, conf)
        self.assertTrue(plug.enabled)


class TestDoctestPlugin(unittest.TestCase):
    def setUp(self):
        self.p = sys.path[:]

    def tearDown(self):
        sys.path = self.p[:]

    def test_add_options(self):
        # Doctest plugin adds some options...
        conf = Config()
        opt = Bucket()
        parser = MockOptParser()
        plug = Doctest()

        plug.add_options(parser, {})
        o, d = parser.opts[0]
        self.assertEqual(o[0], "--with-doctest")

        o2, d2 = parser.opts[1]
        self.assertEqual(o2[0], "--doctest-tests")

        o3, d3 = parser.opts[2]
        self.assertEqual(o3[0], "--doctest-extension")

    def test_config(self):
        # Test that configuration works properly when both environment
        # and command line specify a doctest extension.
        conf = Config()
        env = {"NOSE_DOCTEST_EXTENSION": "ext"}
        argv = ["--doctest-extension", "txt"]
        dtp = Doctest()
        parser = OptionParser()
        dtp.add_options(parser, env)
        options, args = parser.parse_args(argv)

        self.assertEqual(options.doctestExtension, ["ext", "txt"])

        env = {}
        parser = OptionParser()
        dtp.add_options(parser, env)
        options, args = parser.parse_args(argv)
        self.assertEqual(options.doctestExtension, ["txt"])

    def test_want_file(self):
        # Doctest plugin can select module and/or non-module files.
        conf = Config()
        opt = Bucket()
        plug = Doctest()
        plug.can_configure = True
        plug.configure(opt, conf)

        self.assertTrue(plug.wantFile("foo.py"))
        self.assertFalse(plug.wantFile("bar.txt"))
        self.assertFalse(plug.wantFile("buz.rst"))
        self.assertFalse(plug.wantFile("bing.mov"))

        plug.extension = [".txt", ".rst"]
        self.assertTrue(plug.wantFile("/path/to/foo.py"))
        self.assertTrue(plug.wantFile("/path/to/bar.txt"))
        self.assertTrue(plug.wantFile("/path/to/buz.rst"))
        self.assertFalse(plug.wantFile("/path/to/bing.mov"))

    def test_matches(self):
        # Doctest plugin wants tests from all NON-test modules.
        conf = Config()
        opt = Bucket()
        plug = Doctest()
        plug.can_configure = True
        plug.configure(opt, conf)
        self.assertFalse(plug.matches("test"))
        self.assertTrue(plug.matches("foo"))

    def test_collect_pymodule(self):
        here = os.path.dirname(__file__)
        support = os.path.join(here, "support")
        if support not in sys.path:
            sys.path.insert(0, support)
        import foo.bar.buz

        conf = Config()
        opt = Bucket()
        plug = Doctest()
        plug.can_configure = True
        plug.configure(opt, conf)
        suite = plug.loadTestsFromModule(foo.bar.buz)
        expect = ["[afunc (foo.bar.buz)]"]
        for test in suite:
            self.assertEqual(str(test), expect.pop(0))

    def test_addresses(self):
        here = os.path.dirname(__file__)
        support = os.path.join(here, "support")
        if support not in sys.path:
            sys.path.insert(0, support)
        import foo.bar.buz

        conf = Config()
        opt = Bucket()
        plug = Doctest()
        plug.can_configure = True
        plug.configure(opt, conf)
        suite = plug.loadTestsFromModule(foo.bar.buz)
        for test in suite:
            _, mod, call = test.address()
            self.assertEqual(mod, "foo.bar.buz")
            self.assertIsNone(call)
            for case in test:
                _, mod, call = case.address()
                self.assertEqual(mod, "foo.bar.buz")
                self.assertEqual(call, "afunc")

    def test_collect_txtfile(self):
        here = os.path.abspath(os.path.dirname(__file__))
        support = os.path.join(here, "support")
        fn = os.path.join(support, "foo", "doctests.txt")

        conf = Config()
        opt = Bucket()
        plug = Doctest()
        plug.can_configure = True
        plug.configure(opt, conf)
        plug.extension = [".txt"]
        suite = plug.loadTestsFromFile(fn)
        for test in suite:
            self.assertTrue(str(test).endswith("doctests.txt"))
            self.assertTrue(test.address(), "Test %s has no address" % test)

    def test_collect_no_collect(self):
        # bug http://nose.python-hosting.com/ticket/55
        # we got "iteration over non-sequence" when no files match.
        here = os.path.abspath(os.path.dirname(__file__))
        support = os.path.join(here, "support")
        plug = Doctest()
        for test in plug.loadTestsFromFile(os.path.join(support, "foo")):
            self.fail("Expected no tests, got %s" % test)


class TestAttribPlugin(unittest.TestCase):
    def test_add_options(self):
        plug = AttributeSelector()
        parser = MockOptParser()
        plug.add_options(parser)

        expect = [
            (
                ("-a", "--attr"),
                {
                    "dest": "attr",
                    "action": "append",
                    "default": None,
                    "metavar": "ATTR",
                    "help": "Run only tests that have attributes "
                    "specified by ATTR [NOSE_ATTR]",
                },
            )
        ]

        expect.append(
            (
                ("-A", "--eval-attr"),
                {
                    "dest": "eval_attr",
                    "action": "append",
                    "default": None,
                    "metavar": "EXPR",
                    "help": "Run only tests for whose attributes the "
                    "Python expression EXPR evaluates to True "
                    "[NOSE_EVAL_ATTR]",
                },
            )
        )
        self.assertEqual(parser.opts, expect)

        opt = Bucket()
        opt.attr = ["!slow"]
        plug.configure(opt, Config())
        self.assertTrue(plug.enabled)
        self.assertEqual(plug.attribs, [[("slow", False)]])

        opt.attr = ["fast,quick", "weird=66"]
        plug.configure(opt, Config())
        self.assertEqual(
            plug.attribs,
            [[("fast", True), ("quick", True)], [("weird", "66")]],
        )

        # Don't die on trailing comma.
        opt.attr = ["something,"]
        plug.configure(opt, Config())
        self.assertEqual(plug.attribs, [[("something", True)]])

        opt.attr = None
        opt.eval_attr = ["weird >= 66"]
        plug.configure(opt, Config())
        self.assertEqual(plug.attribs[0][0][0], "weird >= 66")
        self.assertTrue(callable(plug.attribs[0][0][1]))

    def test_basic_attr(self):
        def f():
            pass

        f.a = 1

        def g():
            pass

        plug = AttributeSelector()
        plug.attribs = [[("a", True)]]
        self.assertIsNot(plug.wantFunction(f), False)
        self.assertFalse(plug.wantFunction(g))

    def test_class_attr(self):
        class TestP:
            foo = True

            def h(self):
                pass

        def i():
            pass

        plug = AttributeSelector()
        plug.attribs = [[("foo", True)]]
        # Python 3 no longer has unbound methods. A bound method supplies the
        # __self__ relationship that AttributeSelector.wantMethod expects.
        self.assertIsNot(plug.wantMethod(TestP().h), False)
        self.assertFalse(plug.wantFunction(i))

    def test_eval_attr(self):
        def f():
            pass

        f.monkey = 2

        def g():
            pass

        g.monkey = 6

        def h():
            pass

        h.monkey = 5

        cnf = Config()
        opt = Bucket()
        opt.eval_attr = "monkey > 5"
        plug = AttributeSelector()
        plug.configure(opt, cnf)

        self.assertFalse(plug.wantFunction(f))
        self.assertIsNot(plug.wantFunction(g), False)
        self.assertFalse(plug.wantFunction(h))

    def test_attr_a_b(self):
        def f1():
            pass

        f1.tags = ["a", "b"]

        def f2():
            pass

        f2.tags = ["a", "c"]

        def f3():
            pass

        f3.tags = ["b", "c"]

        def f4():
            pass

        f4.tags = ["c", "d"]

        cnf = Config()
        parser = OptionParser()
        plug = AttributeSelector()

        plug.add_options(parser)

        # OR
        opt, args = parser.parse_args(["test", "-a", "tags=a", "-a", "tags=b"])

        self.assertIsNone(plug.wantFunction(f1))
        self.assertIsNone(plug.wantFunction(f2))
        self.assertIsNone(plug.wantFunction(f3))
        self.assertFalse(plug.wantFunction(f4))

        # AND
        opt, args = parser.parse_args(["test", "-a", "tags=a,tags=b"])

        self.assertIsNone(plug.wantFunction(f1))
        self.assertFalse(plug.wantFunction(f2))
        self.assertFalse(plug.wantFunction(f3))
        self.assertFalse(plug.wantFunction(f4))


class TestFailureDetailPlugin(unittest.TestCase):
    def test_formatFailure(self):
        class DummyError(Exception):
            pass

        try:
            raise DummyError
        except DummyError:
            exc_info = sys.exc_info()

        plug = FailureDetail()
        ec, ev, tb = plug.formatFailure(self, exc_info)
        self.assertIs(exc_info[0], ec)
        self.assertIs(exc_info[2], tb)
        self.assertIsNotNone(self.tbinfo)

        exc_info = (exc_info[0], exc_info[1], None)
        ec, ev, tb = plug.formatFailure(self, exc_info)
        self.assertIsNone(self.tbinfo)


class TestProfPlugin(unittest.TestCase):
    def setUp(self):
        if not Profile.available():
            raise SkipTest("profile plugin not available; skipping")

    def test_options(self):
        parser = OptionParser()
        conf = Config()
        plug = Profile()

        plug.add_options(parser, {})
        opts = [o._long_opts[0] for o in parser.option_list]
        self.assertIn("--profile-sort", opts)
        self.assertIn("--profile-stats-file", opts)
        self.assertIn("--with-profile", opts)
        self.assertIn("--profile-restrict", opts)

    def test_begin(self):
        plug = Profile()
        plug.pfile = tempfile.mkstemp()[1]
        try:
            plug.begin()
            self.assertTrue(plug.prof)
        finally:
            plug.finalize(None)

    def test_prepare_test(self):
        result_data = {}

        class Dummy:
            def runcall(self, func, result):
                result[1] = func(), "wrapped"

        def func():
            return "func"

        plug = Profile()
        plug.prof = Dummy()
        result = plug.prepareTest(func)
        try:
            result(result_data)
            self.assertEqual(result_data[1], ("func", "wrapped"))
        finally:
            plug.finalize(None)

    def test_finalize(self):
        def func():
            pass

        plug = Profile()
        plug.begin()
        plug.prepareTest(func)
        pfile = plug.pfile
        try:
            self.assertTrue(os.path.exists(pfile))
        finally:
            plug.finalize(None)
        self.assertFalse(os.path.exists(pfile))


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from io import StringIO
from nose.core import TestProgram
from nose.config import Config
from nose.result import TextTestResult

here = os.path.dirname(__file__)
support = os.path.join(here, 'support')


class TestRunner(unittest.TextTestRunner):
    def _makeResult(self):
        self.result = TextTestResult(
            self.stream, self.descriptions, self.verbosity)
        return self.result


class TestBuggyGenerators(unittest.TestCase):
    def test_run_buggy_generators(self):
        stream = StringIO()
        runner = TestRunner(stream=stream)
        prog = TestProgram(
            argv=['nosetests',
                  os.path.join(support, 'test_buggy_generators.py')],
            testRunner=runner,
            config=Config(),
            exit=False)
        res = runner.result
        print("")
        stream.getvalue()
        self.assertEqual(res.testsRun, 9,
                         "Expected to run 9 tests, ran %s" % res.testsRun)
        assert not res.wasSuccessful()
        assert not res.failures

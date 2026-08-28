import os
import sys

here = os.path.dirname(__file__)
flag = os.path.join(here, "shared_flag")

_multiprocess_shared_ = 1


def _log(val):
    with open(flag, "a+") as flag_file:
        flag_file.write(val)
        flag_file.write("\n")


def _clear():
    if os.path.isfile(flag):
        os.unlink(flag)


def logged():
    with open(flag, "r") as flag_file:
        return list(flag_file)


def setup():
    print("setup called", file=sys.stderr)
    _log("setup")


def teardown():
    print("teardown called", file=sys.stderr)
    _clear()


def test_a():
    assert len(logged()) == 1, "len(%s) != 1" % len(logged())


def test_b():
    assert len(logged()) == 1, "len(%s) != 1" % len(logged())


class TestMe:
    @classmethod
    def setup_class(cls):
        cls._setup = True

    def test_one(self):
        assert self._setup, "Class was not set up"

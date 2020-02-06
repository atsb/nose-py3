from unittest import TestCase

from nose.plugins.attrib import attr


@attr("b")
def test_b():
    assert 1 == 1


class TestBase(TestCase):
    def test_a(self):
        assert 1 == 1


class TestDerived(TestBase):
    @attr("a")
    def test_a(self):
        assert 1 == 1

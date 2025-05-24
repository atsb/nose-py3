import os

from nose.plugins.skip import SkipTest

try:
    from pkg_resources import EntryPoint
except ImportError:
    raise SkipTest("No setuptools available; skipping")

here = os.path.dirname(__file__)
support = os.path.join(here, 'support')
ep = os.path.join(support, 'ep')


def test_plugin_entrypoint_is_loadable():
    ep_path = os.path.join(ep, 'Some_plugin.egg-info', 'entry_points.txt')
    ep_file = open(ep_path, 'r', encoding='utf-8')
    lines = ep_file.readlines()
    ep_file.close()
    assert EntryPoint.parse_map(lines)

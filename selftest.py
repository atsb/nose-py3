#!/usr/bin/env python

"""Test the copy of nose in this directory, by running that nose against itself.

You can test nose using nose in other ways, but if you don't use this script,
you might have one installation of nose testing another installation, which is
not supported.
"""

# More detail:

# In the absence of some sort of deep renaming magic, nose can't reasonably
# test a different installation of itself, given the existence of the global
# module registry sys.modules .

# If installed system-wide with setuptools, setuptools (via the site-packages
# easy-install.pth) takes you at your word and ensures that the installed nose
# comes first on sys.path .  So the only way to test a copy of nose other than
# the installed one is to install that version (e.g. by running python setup.py
# develop).

# This script provides a way of running nose on nose's own tests without
# installing the version to be tested, nor uninstalling the currently-installed
# version.

import glob
import os
import sys

import importlib.metadata


# replacement for old pkg_resources
def importlib_env(search_paths):
    distributions = {}
    for path in search_paths:
        try:
            for distribution in importlib.metadata.distributions(path=path):
                distributions[distribution.metadata['Name']] = distribution
        except Exception as e:
            print(f"Error processing path {path}: {e}")
    return distributions


if __name__ == "__main__":
    this_dir = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
    lib_dirs = [this_dir]
    test_dir = this_dir

    lib_dirs = glob.glob(os.path.join(this_dir, 'build', 'lib*'))
    test_dir = os.path.join(this_dir, 'build', 'tests')
    if not os.path.isdir(test_dir):
        raise Exception(
            "Error: %s does not exist.  Use the setup.py 'build_tests' command to create it." % (
                test_dir,))

    env = importlib_env(lib_dirs)

    distributions = env["nose-py3"]
    if not distributions:
        raise Exception("No nose distibution has been built")
    elif len(distributions) != 1:
        raise Exception("More than one nose distribution found")

    dist = distributions[0]
    dist.activate()

    # Always make sure our chosen test dir is first on the path
    sys.path.insert(0, test_dir)
    import nose

    nose.run_exit()

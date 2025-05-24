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

import os
import sys

# Removed: import glob
# Removed: import importlib.metadata
# Removed: importlib_env function

if __name__ == "__main__":
    this_dir = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))

    # Ensure the local 'nose' library is on the path
    # this_dir is the project root, which contains the 'nose' package.
    sys.path.insert(0, this_dir)

    # Define test source directories relative to the project root
    test_source_dirs_relative = [
        "functional_tests",
        "unit_tests",
        os.path.join("doc", "doc_tests")
    ]

    # Add test source directories to sys.path
    # We insert them after the project root to ensure local 'nose' is preferred,
    # and then in reverse order so the first one in the list is searched first.
    for test_subdir in reversed(test_source_dirs_relative):
        abs_test_dir = os.path.join(this_dir, test_subdir)
        if not os.path.isdir(abs_test_dir):
            # This is a basic sanity check, though setup.py's test_dirs should be accurate.
            print(f"Warning: Test directory {abs_test_dir} not found, skipping.")
        else:
            sys.path.insert(1, abs_test_dir) # Insert after project_root

    # Removed: lib_dirs = glob.glob(os.path.join(this_dir, 'build', 'lib*'))
    # Removed: test_dir = os.path.join(this_dir, 'build', 'tests')
    # Removed: if not os.path.isdir(test_dir): ... (existence check for build/tests)

    # Removed: env = importlib_env(lib_dirs)
    # Removed: distributions = env["nose-py3"]
    # Removed: if not distributions: ...
    # Removed: elif len(distributions) != 1: ...
    # Removed: dist = distributions[0]
    # Removed: dist.activate()

    # Removed: sys.path.insert(0, test_dir) # This was for the build/tests directory

    # Import nose (should now pick up the local version)
    import nose

    # Run tests
    nose.run_exit()

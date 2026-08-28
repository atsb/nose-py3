"""Profile plugin using Python's cProfile profiler.

This plugin runs tests under cProfile. Use ``--with-profile`` or the
``NOSE_WITH_PROFILE`` environment variable to enable it.

Profiler output can be controlled with ``--profile-sort`` and
``--profile-restrict``. The profiler statistics file may be changed with
``--profile-stats-file``.
"""

import cProfile
import logging
import os
import tempfile

from nose.plugins.base import Plugin
from nose.util import tolist


log = logging.getLogger("nose.plugins")


class Profile(Plugin):
    """Use this plugin to run tests using the cProfile profiler."""

    pfile = None
    clean_stats_file = False

    @classmethod
    def available(cls):
        """Return whether cProfile is available."""
        return cProfile is not None

    def options(self, parser, env):
        """Register command-line options."""
        if not self.available():
            return

        super().options(parser, env)

        parser.add_option(
            "--profile-sort",
            action="store",
            dest="profile_sort",
            default=env.get("NOSE_PROFILE_SORT", "cumulative"),
            metavar="SORT",
            help="Set sort order for profiler output",
        )
        parser.add_option(
            "--profile-stats-file",
            action="store",
            dest="profile_stats_file",
            metavar="FILE",
            default=env.get("NOSE_PROFILE_STATS_FILE"),
            help="Profiler stats file; default is a new temp file on each run",
        )
        parser.add_option(
            "--profile-restrict",
            action="append",
            dest="profile_restrict",
            metavar="RESTRICT",
            default=env.get("NOSE_PROFILE_RESTRICT"),
            help="Restrict profiler output. See help for pstats.Stats for details",
        )

    def begin(self):
        """Create the profile stats file and load the profiler."""
        if not self.available():
            return

        self._create_pfile()
        self.prof = cProfile.Profile(self.pfile)

    def configure(self, options, conf):
        """Configure the plugin."""
        if not self.available():
            self.enabled = False
            return

        super().configure(options, conf)
        self.conf = conf

        if options.profile_stats_file:
            self.pfile = options.profile_stats_file
            self.clean_stats_file = False
        else:
            self.pfile = None
            self.clean_stats_file = True

        self.fileno = None
        self.sort = options.profile_sort
        self.restrict = tolist(options.profile_restrict)

    def prepareTest(self, test):
        """Wrap the entire test run in ``prof.runcall``."""
        if not self.available():
            return

        log.debug("preparing test %s", test)

        def run_and_profile(result, prof=self.prof, test=test):
            self._create_pfile()
            prof.runcall(test, result)

        return run_and_profile

    def report(self, stream):
        """Output the profiler report."""
        log.debug("printing profiler report")
        self.prof.disable()
        prof_stats = cProfile.Profile(self.pfile)

        # Preserve the historical nose behavior: print the report to the
        # supplied stream rather than the process-wide stdout.
        stream = getattr(stream, "write", stream)
        self._print_stats(prof_stats, stream)

    def _print_stats(self, prof_stats, stream):
        """Print profiler statistics to *stream*."""
        import pstats

        prof_stats.disable() if hasattr(prof_stats, "disable") else None
        stats = pstats.Stats(prof_stats)

        if self.restrict:
            log.debug("setting profiler restriction to %s", self.restrict)
            stats.print_stats(*self.restrict)
        else:
            stats.sort_stats(self.sort)
            stats.print_stats()

    def finalize(self, result):
        """Clean up the stats file, if configured to do so."""
        if not self.available():
            return

        try:
            self.prof.disable()
        except AttributeError:
            pass

        if self.clean_stats_file:
            if self.fileno:
                try:
                    os.close(self.fileno)
                except OSError:
                    pass

            try:
                os.unlink(self.pfile)
            except OSError:
                pass

        return None

    def _create_pfile(self):
        if not self.pfile:
            self.fileno, self.pfile = tempfile.mkstemp()
            self.clean_stats_file = True

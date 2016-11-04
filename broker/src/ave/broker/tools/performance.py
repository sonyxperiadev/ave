# origin: profilehooks 1.6 (http://pypi.python.org/pypi/profilehooks) :
'''
Copyright (c) 2004--2012 Marius Gedminas <marius@pov.lt>
Copyright (c) 2007 Hanno Schlichting
Copyright (c) 2008 Florian Schulze

Released under the MIT licence since December 2006:

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.
'''

import atexit
import inspect
import sys
import re

import cProfile
import profile
import pstats

def prof(fn=None, skip=0, filename=None, immediate=False, dirs=False,
            sort=None, entries=40):
    """Mark `fn` for profiling.

    If `skip` is > 0, first `skip` calls to `fn` will not be profiled.

    If `immediate` is False, profiling results will be printed to
    sys.stdout on program termination.  Otherwise results will be printed
    after each call.

    If `dirs` is False only the name of the file will be printed.
    Otherwise the full path is used.

    `sort` can be a list of sort keys (defaulting to ['cumulative',
    'time', 'calls']).  The following ones are recognized::

        'calls'      -- call count
        'cumulative' -- cumulative time
        'file'       -- file name
        'line'       -- line number
        'module'     -- file name
        'name'       -- function name
        'nfl'        -- name/file/line
        'pcalls'     -- call count
        'stdname'    -- standard name
        'time'       -- internal time

    `entries` limits the output to the first N entries.

    If `filename` is specified, the profile stats will be stored in the
    named file.  You can load them pstats.Stats(filename).

    Usage::

        def fn(...):
            ...
        fn = profile(fn, skip=1)

    If you are using Python 2.4, you should be able to use the decorator
    syntax::

        @profile(skip=3)
        def fn(...):
            ...

    or just ::

        @profile
        def fn(...):
            ...

    """
    if fn is None: # @profile() syntax -- we are a decorator maker
        def decorator(fn):
            return prof(fn, skip=skip, filename=filename,
                           immediate=immediate, dirs=dirs,
                           sort=sort, entries=entries)
        return decorator
    # @profile syntax -- we are a decorator.
    fp = FuncProfile(fn, skip=skip, filename=filename,
                        immediate=immediate, dirs=dirs,
                        sort=sort, entries=entries)
    # We cannot return fp or fp.__call__ directly as that would break method
    # definitions, instead we need to return a plain function.
    def new_fn(*args, **kw):
        return fp(*args, **kw)
    new_fn.__doc__ = fn.__doc__
    new_fn.__name__ = fn.__name__
    new_fn.__dict__ = fn.__dict__
    new_fn.__module__ = fn.__module__
    return new_fn


class FuncProfile(object):
    """Profiler for a function (uses profile)."""

    # This flag is shared between all instances
    in_profiler = False

    Profile = cProfile.Profile

    def __init__(self, fn, skip=0, filename=None, immediate=False, dirs=False,
                 sort=None, entries=40):
        """Creates a profiler for a function.

        Every profiler has its own log file (the name of which is derived
        from the function name).

        FuncProfile registers an atexit handler that prints profiling
        information to sys.stderr when the program terminates.
        """
        self.fn = fn
        self.skip = skip
        self.filename = filename
        self.immediate = immediate
        self.dirs = dirs
        self.sort = sort or ('cumulative', 'time', 'calls')
        if isinstance(self.sort, str):
            self.sort = (self.sort, )
        self.entries = entries
        self.reset_stats()
        atexit.register(self.atexit)

    def __call__(self, *args, **kw):
        """Profile a singe call to the function."""
        self.ncalls += 1
        if self.skip > 0:
            self.skip -= 1
            self.skipped += 1
            return self.fn(*args, **kw)
        if FuncProfile.in_profiler:
            # handle recursive calls
            return self.fn(*args, **kw)
        # You cannot reuse the same profiler for many calls and accumulate
        # stats that way.  :-/
        profiler = cProfile.Profile()
        try:
            FuncProfile.in_profiler = True
            return profiler.runcall(self.fn, *args, **kw)
        finally:
            FuncProfile.in_profiler = False
            self.stats.add(profiler)
            if self.immediate:
                self.print_stats()
                self.reset_stats()

    def print_stats(self):
        """Print profile information to sys.stdout."""
        funcname = self.fn.__name__
        filename = self.fn.__code__.co_filename
        lineno = self.fn.__code__.co_firstlineno
        print("")
        print("*** PROFILER RESULTS ***")
        print("%s (%s:%s)" % (funcname, filename, lineno))
        if self.skipped:
            skipped = "(%d calls not profiled)" % self.skipped
        else:
            skipped = ""
        print("function called %d times%s" % (self.ncalls, skipped))
        print("")
        stats = self.stats
        if self.filename:
            stats.dump_stats(self.filename)
        if not self.dirs:
            stats.strip_dirs()
        stats.sort_stats(*self.sort)
        stats.print_stats(self.entries)

    def reset_stats(self):
        """Reset accumulated profiler statistics."""
        # Note: not using self.Profile, since pstats.Stats() fails then
        self.stats = pstats.Stats(profile.Profile())
        self.ncalls = 0
        self.skipped = 0

    def atexit(self):
        """Stop profiling and print profile information to sys.stdout.

        This function is registered as an atexit hook.
        """
        if not self.immediate:
            self.print_stats()


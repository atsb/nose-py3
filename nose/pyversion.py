"""
This module contains fixups for using nose under different versions of Python.
"""
import inspect
import os
import sys
import traceback

import nose.util

__all__ = ['make_instancemethod', 'cmp_to_key', 'sort_list',
           'UNICODE_STRINGS', 'unbound_method', 'ismethod',
           'bytes_', 'is_base_exception', 'force_unicode', 'exc_to_unicode',
           'format_exception', 'isgenerator']

UNICODE_STRINGS = True


def force_unicode(s):
    return str(s)


# new.instancemethod() is obsolete for new-style classes (Python 3.x)
# We need to use descriptor methods instead.

def make_instancemethod(function, instance):
    return function.__get__(instance, instance.__class__)


# To be forward-compatible, we do all list sorts using keys instead of cmp
# functions.  However, part of the unittest.TestLoader API involves a
# user-provideable cmp function, so we need some way to convert that.
def cmp_to_key(mycmp):
    """Convert a cmp= function into a key= function"""

    class Key(object):
        def __init__(self, obj):
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0

    return Key


# Python 2.3 also does not support list-sorting by key, so we need to convert
# keys to cmp functions if we're running on old Python..
def sort_list(l, key, reverse=False):
    sorted_list = sorted(l, key=key, reverse=reverse)
    return sorted_list


# The following emulates the behavior (we need) of an 'unbound method' under
# Python 3.x (namely, the ability to have a class associated with a function
# definition so that things can do stuff based on its associated class)
class UnboundMethod:
    def __init__(self, cls, func):
        # Make sure we have all the same attributes as the original function,
        # so that the AttributeSelector plugin will work correctly...
        self.__dict__ = func.__dict__.copy()
        self._func = func
        self.__self__ = UnboundSelf(cls)
        self.__doc__ = getattr(func, '__doc__', None)

    def address(self):
        cls = self.__self__.cls
        modname = cls.__module__
        module = sys.modules[modname]
        filename = getattr(module, '__file__', None)
        if filename is not None:
            filename = os.path.abspath(filename)
        return (nose.util.src(filename), modname, "%s.%s" % (cls.__name__,
                                                             self._func.__name__))

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def __getattr__(self, attr):
        return getattr(self._func, attr)

    def __repr__(self):
        return '<unbound method %s.%s>' % (self.__self__.cls.__name__,
                                           self._func.__name__)

    @property
    def func(self):
        return self._func


class UnboundSelf:
    def __init__(self, cls):
        self.cls = cls

    # We have to do this hackery because Python won't let us override the
    # __class__ attribute...
    def __getattribute__(self, attr):
        if attr == '__class__':
            return self.cls
        else:
            return object.__getattribute__(self, attr)


def unbound_method(cls, func):
    if inspect.ismethod(func):
        return func
    if not inspect.isfunction(func):
        raise TypeError('%s is not a function' % (repr(func),))
    return UnboundMethod(cls, func)


def ismethod(obj):
    return inspect.ismethod(obj) or isinstance(obj, UnboundMethod)


# Make a pseudo-bytes function that can be called without the encoding arg:
if sys.version_info >= (3, 0):
    def bytes_(s, encoding='utf8'):
        if isinstance(s, bytes):
            return s
        return bytes(s, encoding)
else:
    def bytes_(s, encoding=None):
        return str(s)


def isgenerator(o):
    if isinstance(o, UnboundMethod):
        o = o.func
        return inspect.isgeneratorfunction(o) or inspect.isgenerator(o)


# Make a function to help check if an exception is derived from BaseException.
# In Python 2.4, we just use Exception instead.
def is_base_exception(exc):
    return isinstance(exc, BaseException)


def exc_to_unicode(ev):
    return str(ev)


def format_exception(exc_info, encoding='UTF-8'):
    ec, ev, tb = exc_info

    # Our exception object may have been turned into a string, and Python 3's
    # traceback.format_exception() doesn't take kindly to that (it expects an
    # actual exception object).  So we work around it, by doing the work
    # ourselves if ev is not an exception object.
    if not is_base_exception(ev):
        tb_data = force_unicode(
            ''.join(traceback.format_tb(tb)))
        ev = exc_to_unicode(ev)
        return tb_data + ev
    else:
        return force_unicode(
            ''.join(traceback.format_exception(*exc_info)))

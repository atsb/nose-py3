"""
ErrorClass Plugins
------------------

ErrorClass plugins provide an easy way to add support for custom
handling of particular classes of exceptions.

An ErrorClass plugin defines one or more ErrorClasses and how each is
handled and reported on. Each error class is stored in a different
attribute on the result, and reported separately. Each error class must
indicate the exceptions that fall under that class, the label to use
for reporting, and whether exceptions of the class should be
considered as failures for the whole test run.
"""

from nose.plugins.base import Plugin
from nose.pyversion import make_instancemethod
from nose.result import NoseTextTestResult
from nose.util import isclass


class MetaErrorClass(type):
    """Metaclass for ErrorClassPlugins that allows error classes to be
    set up in a declarative manner.
    """

    def __init__(cls, name, bases, attr):
        errorClasses = []
        for name, detail in attr.items():
            if isinstance(detail, ErrorClass):
                attr.pop(name)
                for classes in detail:
                    errorClasses.append(
                        (classes, (name, detail.label, detail.isfailure)))
        super(MetaErrorClass, cls).__init__(name, bases, attr)
        cls.errorClasses = tuple(errorClasses)


class ErrorClass(object):
    def __init__(self, *errorClasses, **kw):
        self.errorClasses = errorClasses
        try:
            for key in ('label', 'isfailure'):
                setattr(self, key, kw.pop(key))
        except KeyError:
            raise TypeError("%r is a required named argument for ErrorClass"
                            % key)

    def __iter__(self):
        return iter(self.errorClasses)


class ErrorClassPlugin(Plugin):
    """
    Base class for ErrorClass plugins. Subclass this class and declare the
    exceptions that you wish to handle as attributes of the subclass.
    """
    __metaclass__ = MetaErrorClass
    score = 1000
    errorClasses = ()

    def addError(self, test, err):
        err_cls, a, b = err
        if not isclass(err_cls):
            return
        classes = [e[0] for e in self.errorClasses]
        if filter(lambda c: issubclass(err_cls, c), classes):
            return True

    def prepareTestResult(self, result):
        if not hasattr(result, 'errorClasses'):
            self.patchResult(result)
        for cls, (storage_attr, label, isfail) in self.errorClasses:
            if cls not in result.errorClasses:
                storage = getattr(result, storage_attr, [])
                setattr(result, storage_attr, storage)
                result.errorClasses[cls] = (storage, label, isfail)

    def patchResult(self, result):
        result.printLabel = print_label_patch(result)
        result._orig_addError, result.addError = \
            result.addError, add_error_patch(result)
        result._orig_wasSuccessful, result.wasSuccessful = \
            result.wasSuccessful, wassuccessful_patch(result)
        if hasattr(result, 'printErrors'):
            result._orig_printErrors, result.printErrors = \
                result.printErrors, print_errors_patch(result)
        if hasattr(result, 'addSkip'):
            result._orig_addSkip, result.addSkip = \
                result.addSkip, add_skip_patch(result)
        result.errorClasses = {}


def add_error_patch(result):
    """Create a new addError method to patch into a result instance
    that recognizes the errorClasses attribute and deals with
    errorclasses correctly.
    """
    return make_instancemethod(NoseTextTestResult.addError, result)


def print_errors_patch(result):
    """Create a new printErrors method that prints errorClasses items
    as well.
    """
    return make_instancemethod(NoseTextTestResult.printErrors, result)


def print_label_patch(result):
    """Create a new printLabel method that prints errorClasses items
    as well.
    """
    return make_instancemethod(NoseTextTestResult.printLabel, result)


def wassuccessful_patch(result):
    """Create a new wasSuccessful method that checks errorClasses for
    exceptions that were put into other slots than error or failure
    but that still count as not success.
    """
    return make_instancemethod(NoseTextTestResult.wasSuccessful, result)


def add_skip_patch(result):
    """Create a new addSkip method to patch into a result instance
    that delegates to addError.
    """
    return make_instancemethod(NoseTextTestResult.addSkip, result)


if __name__ == '__main__':
    import doctest

    doctest.testmod()

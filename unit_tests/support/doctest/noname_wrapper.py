import importlib
import importlib.util
import sys, os


# replacement with new importlib function wrapper
def load_source(name, filepath):
    spec = importlib.util.spec_from_file_location(name, filepath)
    if spec is None:
        raise ImportError(f"Error: Can not load the module {name} from {filepath}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[name] = module
    return module


def __bootstrap__():
    """ Import the code in ``noname_wrapped.not_py`` in file as our own name

    This is a simplified version of the wrapper that setuptools writes for
    dynamic libraries when installing.
    """

    here = os.path.join(os.path.dirname(__file__))
    load_source(__name__, os.path.join(here, 'noname_wrapped.not_py'))


__bootstrap__()

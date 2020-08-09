import sys
import os
import re
import importlib
import warnings


is_pypy = '__pypy__' in sys.builtin_module_names


def warn_distutils_present():
    if 'distutils' not in sys.modules:
        return
    if is_pypy and sys.version_info < (3, 7):
        # PyPy for 3.6 unconditionally imports distutils, so bypass the warning
        # https://foss.heptapod.net/pypy/pypy/-/blob/be829135bc0d758997b3566062999ee8b23872b4/lib-python/3/site.py#L250
        return
    warnings.warn(
        "Distutils was imported before Setuptools. This usage is discouraged "
        "and may exhibit undesirable behaviors or errors. Please use "
        "Setuptools' objects directly or at least import Setuptools first.")


def clear_distutils():
    if 'distutils' not in sys.modules:
        return
    warnings.warn("Setuptools is replacing distutils.")
    mods = [name for name in sys.modules if re.match(r'distutils\b', name)]
    for name in mods:
        del sys.modules[name]


def enabled():
    """
    Allow selection of distutils by environment variable.
    """
    which = os.environ.get('SETUPTOOLS_USE_DISTUTILS', 'stdlib')
    return which == 'local'


def ensure_local_distutils():
    clear_distutils()
    distutils = importlib.import_module('setuptools._distutils')
    distutils.__name__ = 'distutils'
    sys.modules['distutils'] = distutils

    # sanity check that submodules load as expected
    core = importlib.import_module('distutils.core')
    assert '_distutils' in core.__file__, core.__file__


def do_override():
    """
    Ensure that the local copy of distutils is preferred over stdlib.

    See https://github.com/pypa/setuptools/issues/417#issuecomment-392298401
    for more motivation.
    """
    warn_distutils_present()
    if enabled():
        ensure_local_distutils()


class DistutilsMetaFinder:
    def find_spec(self, fullname, path, target=None):
        if path is not None or fullname != "distutils":
            return None

        return self.get_distutils_spec()

    def get_distutils_spec(self):
        import importlib.util

        class DistutilsLoader(importlib.util.abc.Loader):

            def create_module(self, spec):
                return importlib.import_module('._distutils', 'setuptools')

            def exec_module(self, module):
                pass

        return importlib.util.spec_from_loader('distutils', DistutilsLoader())


DISTUTILS_FINDER = DistutilsMetaFinder()


def add_shim():
    sys.meta_path.insert(0, DISTUTILS_FINDER)


def remove_shim():
    try:
        sys.meta_path.remove(DISTUTILS_FINDER)
    except ValueError:
        pass
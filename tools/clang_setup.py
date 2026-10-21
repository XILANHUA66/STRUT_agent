"""Locate libclang and point clang.cindex at it.

The modules used to hard-code an absolute path to a libclang build -- one to
D:\\Software\\Clang\\LLVM\\bin, one to a colleague's conda env
(C:/Users/bondc/.conda/envs/basketball/...), and one to a literal r'path'
placeholder. Since Python executes those assignments at import time and the
last one wins, the tool only ran on the machine it was written on.

The pip ``libclang`` wheel ships the shared library next to the bindings, so
we can just point at that instead of guessing.
"""
import os

import clang.cindex

_LIB_NAMES = ('libclang.dll', 'libclang.so', 'libclang.so.1', 'libclang.dylib')

# the clang python bindings live in <site-packages>/clang
_BINDINGS_DIR = os.path.dirname(os.path.abspath(clang.cindex.__file__))


def bundled_library_path():
    """Path of the libclang shipped with the ``libclang`` wheel, or None."""
    native = os.path.join(_BINDINGS_DIR, 'native')
    for name in _LIB_NAMES:
        candidate = os.path.join(native, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def use_bundled_libclang():
    """Point clang.cindex at the bundled libclang and return the path used.

    Returns None when the wheel is not installed, in which case clang.cindex
    falls back to whatever the platform can find on its own.
    """
    path = bundled_library_path()
    if path:
        clang.cindex.Config.set_library_file(path)
    return path

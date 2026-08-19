"""Loader for the cuvis SWIG binding.

Beyond setting up the library search path, this module reconciles the extension with the
cuvis library actually installed on the machine. The two are built together and are
always in sync at build time, but the library deployed on a user's machine can be older
and simply not export functions the extension imports. Left alone that fails the import
with an opaque loader error and takes down every consumer, including the ones that never
wanted the missing feature.

So, in the order it happens below: the cuvis library is opened by absolute path, the
extension is loaded in a way that survives missing symbols (delay loaded on Windows,
lazily bound on Linux), the functions it needs are read back out of the built module
itself, each is probed against the library, and whatever is missing is replaced by a stub
that raises when called.

What this publishes on the `cuvis_il` module, for a consumer such as cuvis.python:

    missing_symbols         functions the loaded library does not export
    library_path            the file that was loaded
    library_version         how that library reports itself
    built_against_version   how the library this was compiled against reported itself
    library_hash            the build hash out of each of those two banners, which is
    built_against_hash      what tells two builds of one version apart
"""
import ctypes
import os
import platform
import re
import sys
import warnings

from ._imports import required_cuvis_symbols

lib_dir = os.getenv("CUVIS")
if lib_dir is None:
    # Raise (do not sys.exit): this module is imported lazily by the SDK, and killing the
    # host process on a missing env var would take down consumers that only wanted the
    # import-safe cuvis.ipc path. Raising surfaces a clear error at first SDK use instead.
    raise ImportError("CUVIS environmental variable is not set!")

_IS_WINDOWS = platform.system() == "Windows"
if _IS_WINDOWS:
    os.add_dll_directory(lib_dir)
    # cuvis.dll depends on the CUDA runtime (e.g. cublas64_13, npp*_13). Python 3.8+ does
    # not search PATH for an extension module's dependencies, so add the CUDA toolkit bin
    # dirs explicitly. CUDA_PATH is set by the toolkit installer; CUDA 13 keeps the math
    # libs under bin\x64.
    _cuda = os.getenv("CUDA_PATH")
    if _cuda:
        for _sub in ("bin", os.path.join("bin", "x64")):
            _d = os.path.join(_cuda, _sub)
            if os.path.isdir(_d):
                os.add_dll_directory(_d)
    add_il = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    os.environ['PATH'] += os.pathsep + add_il
    sys.path.append(str(add_il))
elif platform.system() == 'Linux':
    os.environ['PATH'] = lib_dir + os.pathsep + os.environ['PATH']
else:
    raise NotImplementedError('Invalid operating system detected!')


def _open_cuvis_library():
    """Load the cuvis library and return it together with the path that worked.

    Loading it here, before the extension binds anything, pins the library CUVIS points
    at. That matters on Windows: the delay load helper calls
    LoadLibraryExA("cuvis.dll", NULL, 0), which ignores os.add_dll_directory and would
    otherwise take any cuvis.dll reachable through the ordinary search order, the current
    directory included. Once ours is in the process under that base name, the helper
    binds to it.
    """
    name = "cuvis.dll" if _IS_WINDOWS else "libcuvis.so"
    load = ctypes.WinDLL if _IS_WINDOWS else ctypes.CDLL
    failures = []
    for candidate in (os.path.join(lib_dir, name), name):   # ours, then the search order
        try:
            return load(candidate), candidate
        except OSError as exc:
            failures.append("{}: {}".format(candidate, exc))
    raise ImportError("cuvis library could not be loaded from {}: {}"
                      .format(lib_dir, "; ".join(failures)))


_cuvis_library, _cuvis_library_path = _open_cuvis_library()


def _import_extension():
    """Import the extension so that a missing symbol does not fail the load.

    Windows needs nothing: cuvis.dll is delay loaded. Linux does, because CPython dlopens
    extensions with RTLD_NOW, which resolves every undefined symbol up front. RTLD_LAZY
    defers function symbols, and cuvis.h exports no data symbols, so the whole surface is
    covered. numpy is imported first to keep its own extensions off the lazy path.
    """
    if _IS_WINDOWS:
        from . import cuvis_il
        return cuvis_il
    try:
        import numpy  # noqa: F401
    except ImportError:
        pass
    previous = sys.getdlopenflags()
    # Process global, not thread local: a concurrent import in this window also gets lazy
    # binding, which is harmless.
    sys.setdlopenflags(os.RTLD_LAZY | os.RTLD_LOCAL)
    try:
        from . import cuvis_il
    finally:
        sys.setdlopenflags(previous)
    return cuvis_il


cuvis_il = _import_extension()


def _entry_point_for(symbol):
    """The module attribute through which `symbol` can be reached, or None.

    A wrapped function keeps its own name; the handful that are %ignore'd in the SWIG
    interface are reached through a hand-written helper that appends _swig. That is a
    naming convention the interface already enforces, not a list of names.
    """
    return next((name for name in (symbol, symbol + "_swig")
                 if hasattr(cuvis_il, name)), None)


def _needed_symbols():
    """The cuvis functions the built extension expects the library to export."""
    return required_cuvis_symbols(cuvis_il._cuvis_pyil.__file__,
                                  lambda name: _entry_point_for(name) is not None)


def _stub(symbol, attribute):
    """A stand-in for an absent function, explaining the absence when it is called."""
    def raise_unavailable(*_args, **_kwargs):
        raise RuntimeError(
            "cuvis: '{}' is not exported by the cuvis library loaded from {}. That "
            "library is not the one this binding was built against (built against: {}; "
            "loaded: {}).".format(symbol, _cuvis_library_path,
                                  _built_against_version() or "unknown",
                                  _library_version() or "unknown"))
    raise_unavailable.__name__ = attribute
    raise_unavailable.__qualname__ = attribute
    return raise_unavailable


def _shadow(symbol):
    """Replace a symbol's entry points, so reaching it raises instead of crashing."""
    attribute = _entry_point_for(symbol)
    if attribute is None:                       # warned about separately
        return
    for module in (cuvis_il, cuvis_il._cuvis_pyil):
        if hasattr(module, attribute):
            setattr(module, attribute, _stub(symbol, attribute))


def _reconcile_with_library():
    """Make every function the loaded library does not export raise when it is called.

    :return: the names it does not export, sorted.
    """
    try:
        needed = _needed_symbols()
    except Exception as exc:
        # Windows still fails safely: the delay load guard in cuvis_il.i turns the call
        # into a RuntimeError. Linux does not, so say so rather than proceed quietly.
        warnings.warn(
            "cuvis_il: could not determine which cuvis functions this build needs ({}). "
            "A cuvis library missing one of them will {}."
            .format(exc, "raise on call" if _IS_WINDOWS else "abort the process"),
            RuntimeWarning, stacklevel=2)
        return ()

    missing = tuple(sorted(name for name in needed
                           if not hasattr(_cuvis_library, name)))
    # Always empty on Linux, where the needed set is already narrowed to what is
    # reachable through an entry point. It is the Windows case this guards.
    unshadowable = sorted(name for name in needed if _entry_point_for(name) is None)

    for symbol in missing:
        _shadow(symbol)

    if missing:
        warnings.warn(
            "cuvis_il: the cuvis library at {} does not export {}. Calling these raises "
            "RuntimeError; everything else works normally."
            .format(_cuvis_library_path, ", ".join(missing)),
            UserWarning, stacklevel=2)
    if unshadowable:
        warnings.warn(
            "cuvis_il: no Python entry point covers {}, so code reaching them cannot be "
            "guarded".format(", ".join(unshadowable)),
            RuntimeWarning, stacklevel=2)
    return missing


def _built_against_version():
    """The cuvis library this binding was compiled against, or "" if unavailable.

    Reported in the same form as the loaded library reports itself, so the two can be
    compared directly. The extension exposes it as an ordinary wrapped function so every
    target language can reach it, not just Python.
    """
    try:
        return cuvis_il.cuvis_built_against_version()
    except Exception:
        return ""


def _library_version():
    try:
        return cuvis_il.cuvis_version_swig()
    except Exception:
        return ""


def _build_hash(banner):
    """The build hash out of a 'CUBERT SDK v. X.Y.Z build: <hash>' banner, or ""."""
    found = re.search(r"build:\s*([0-9a-fA-F]+)", banner or "")
    return found.group(1) if found else ""


cuvis_il.missing_symbols = _reconcile_with_library()
cuvis_il.library_path = _cuvis_library_path
cuvis_il.built_against_version = _built_against_version()
cuvis_il.library_version = _library_version()
# Both sides report themselves in the same form, so the hash that tells two builds of one
# version apart is parsed the same way out of each. A difference is not a failure, only a
# fact worth having when something else is wrong, hence no warning.
cuvis_il.built_against_hash = _build_hash(cuvis_il.built_against_version)
cuvis_il.library_hash = _build_hash(cuvis_il.library_version)

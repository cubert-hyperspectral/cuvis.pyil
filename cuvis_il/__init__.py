"""Loader for the cuvis SWIG binding.

Beyond setting up the library search path, this module reconciles the extension with
the cuvis library actually installed on the machine. The two are built together and are
always in sync at build time, but the library deployed on a user's machine can be older
and simply not export functions the extension imports. Left alone that fails the import
with an opaque loader error and takes down every consumer, including the ones that never
wanted the missing feature.

So: the extension is loaded in a way that survives missing symbols (delay-loaded on
Windows, lazily bound on Linux), the set of functions it needs is read back out of the
built module itself, each one is probed against the loaded library, and whatever is
missing is replaced by a stub that raises when called. `missing_symbols` names them, so
a consumer such as cuvis.python can decide which features that breaks.

Nothing here contains a list of function names; the needed set comes from the binary.
"""
import ctypes
import os
import platform
import re
import struct
import sys
import warnings

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
    """Load the cuvis library by absolute path and return (handle, path).

    Loading it here, before the extension binds anything, pins the library `CUVIS` points
    at. That matters on Windows: the delay-load helper calls LoadLibraryExA("cuvis.dll",
    NULL, 0), which ignores os.add_dll_directory() and would otherwise pick up any
    cuvis.dll reachable through the ordinary search order, the current directory included.
    Once ours is in the process under that base name, the helper binds to it.
    """
    names = ("cuvis.dll",) if _IS_WINDOWS else ("libcuvis.so",)
    loader = ctypes.WinDLL if _IS_WINDOWS else ctypes.CDLL
    errors = []
    for name in names:
        path = os.path.join(lib_dir, name)
        try:
            return loader(path), path
        except OSError as exc:
            errors.append("{}: {}".format(path, exc))
        try:
            return loader(name), name          # fall back to the platform search order
        except OSError as exc:
            errors.append("{}: {}".format(name, exc))
    raise ImportError("cuvis library could not be loaded from {}: {}"
                      .format(lib_dir, "; ".join(errors)))


_cuvis_library, _cuvis_library_path = _open_cuvis_library()


def _import_extension():
    """Import the extension so that missing symbols do not fail the load.

    Windows needs nothing: cuvis.dll is delay-loaded. Linux does, because CPython dlopens
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
    _previous = sys.getdlopenflags()
    # Process-global, not thread-local: a concurrent import in this window also gets lazy
    # binding, which is harmless.
    sys.setdlopenflags(os.RTLD_LAZY | os.RTLD_LOCAL)
    try:
        from . import cuvis_il
    finally:
        sys.setdlopenflags(_previous)
    return cuvis_il


cuvis_il = _import_extension()


def _needed_from_pe(path, dll_prefix="cuvis"):
    """Names the module imports from cuvis*.dll, read from its own PE headers.

    Covers both the ordinary import descriptor (data directory 1) and the delay-load one
    (directory 13), since delay-loading moves every entry out of the former into the latter.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    coff = struct.unpack_from("<I", data, 0x3C)[0] + 4
    n_sections, = struct.unpack_from("<H", data, coff + 2)
    opt_size, = struct.unpack_from("<H", data, coff + 16)
    opt = coff + 20
    pe32plus = struct.unpack_from("<H", data, opt)[0] == 0x20B
    n_dirs, = struct.unpack_from("<I", data, opt + (108 if pe32plus else 92))
    dir_off = opt + (112 if pe32plus else 96)
    dirs = [struct.unpack_from("<II", data, dir_off + 8 * i) for i in range(n_dirs)]
    image_base, = struct.unpack_from("<Q" if pe32plus else "<I", data, opt + 24)
    sections = []
    for i in range(n_sections):
        vsize, vaddr, rsize, raw = struct.unpack_from("<IIII", data, opt + opt_size + 40 * i + 8)
        sections.append((vaddr, max(vsize, rsize), raw))

    def offset(rva):
        for vaddr, size, raw in sections:
            if vaddr <= rva < vaddr + size:
                return raw + (rva - vaddr)
        raise ValueError("rva {:#x} is outside every section".format(rva))

    def string_at(pos):
        return data[pos:data.index(b"\0", pos)].decode("ascii")

    word, step = ("<Q", 8) if pe32plus else ("<I", 4)
    ordinal_bit = (1 << 63) if pe32plus else (1 << 31)

    def thunk_names(rva, to_rva):
        pos = offset(to_rva(rva))
        while True:
            value, = struct.unpack_from(word, data, pos)
            if not value:
                return
            if not value & ordinal_bit:           # ordinal-only imports carry no name
                yield string_at(offset(to_rva(value)) + 2)
            pos += step

    names = set()
    identity = lambda rva: rva
    if len(dirs) > 1 and dirs[1][0]:
        pos = offset(dirs[1][0])
        while True:
            lookup, _, _, name_rva, address = struct.unpack_from("<IIIII", data, pos)
            if not name_rva:
                break
            if string_at(offset(name_rva)).lower().startswith(dll_prefix):
                names.update(thunk_names(lookup or address, identity))
            pos += 20
    if len(dirs) > 13 and dirs[13][0]:
        pos = offset(dirs[13][0])
        while True:
            attrs, name_rva, _, _, table = struct.unpack_from("<IIIII", data, pos)
            if not name_rva:
                break
            # With bit 0 of the attributes clear the descriptor holds virtual addresses
            # rather than RVAs, as older linkers emitted.
            to_rva = identity if attrs & 1 else (lambda rva: rva - image_base)
            if string_at(offset(to_rva(name_rva))).lower().startswith(dll_prefix):
                names.update(thunk_names(table, to_rva))
            pos += 32
    return names


def _undefined_from_elf(path):
    """Undefined .dynsym entries of the module, i.e. everything it expects from elsewhere."""
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    is64 = data[4] == 2
    endian = "<" if data[5] == 1 else ">"
    if is64:
        sh_off, = struct.unpack_from(endian + "Q", data, 0x28)
        sh_entsize, sh_num = struct.unpack_from(endian + "HH", data, 0x3A)
        sh_fmt, sym_fmt = endian + "IIQQQQIIQQ", endian + "IBBHQQ"
    else:
        sh_off, = struct.unpack_from(endian + "I", data, 0x20)
        sh_entsize, sh_num = struct.unpack_from(endian + "HH", data, 0x2E)
        sh_fmt, sym_fmt = endian + "IIIIIIIIII", endian + "IIIBBH"
    headers = [struct.unpack_from(sh_fmt, data, sh_off + i * sh_entsize) for i in range(sh_num)]
    names = set()
    for header in headers:
        if header[1] != 11:                       # SHT_DYNSYM
            continue
        strtab = headers[header[6]][4]            # sh_link -> .dynstr
        start, size, entsize = header[4], header[5], header[9]
        for pos in range(start, start + size, entsize):
            fields = struct.unpack_from(sym_fmt, data, pos)
            st_name = fields[0]
            st_shndx = fields[3] if is64 else fields[5]
            if st_shndx != 0 or not st_name:      # keep named SHN_UNDEF entries only
                continue
            end = data.index(b"\0", strtab + st_name)
            names.add(data[strtab + st_name:end].decode("ascii", "replace"))
    return names


def _entry_point_for(symbol):
    """The module attribute through which `symbol` can be reached, or None.

    A wrapped function keeps its own name; the handful that are %ignore'd in the SWIG
    interface are reached through a hand-written helper that appends _swig. That is a
    naming convention the interface already enforces, not a list of names.
    """
    for candidate in (symbol, symbol + "_swig"):
        if hasattr(cuvis_il, candidate):
            return candidate
    return None


def _needed_symbols():
    """Function names the built extension expects the cuvis library to export."""
    module_path = cuvis_il._cuvis_pyil.__file__
    if _IS_WINDOWS:
        return _needed_from_pe(module_path)
    # Undefined ELF symbols do not record which library provides them, so keep the ones
    # that correspond to a wrapped entry point. Derived from SWIG's output, not written down.
    return {name for name in _undefined_from_elf(module_path) if _entry_point_for(name)}


def _stub(symbol, attribute):
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


def _reconcile_with_library():
    """Find what the loaded library does not export, and make calling it raise."""
    try:
        needed = _needed_symbols()
    except Exception as exc:
        # Windows still fails safely: the delay-load guard in cuvis_il.i turns the call
        # into a RuntimeError. Linux does not, so say so rather than proceed quietly.
        warnings.warn(
            "cuvis_il: could not determine which cuvis functions this build needs ({}). "
            "A cuvis library missing one of them will {}."
            .format(exc, "raise on call" if _IS_WINDOWS else "abort the process"),
            RuntimeWarning, stacklevel=2)
        cuvis_il.missing_symbols = ()
        return

    missing = sorted(name for name in needed if not hasattr(_cuvis_library, name))
    unshadowable = [name for name in needed if _entry_point_for(name) is None]

    low_level = cuvis_il._cuvis_pyil
    for symbol in missing:
        attribute = _entry_point_for(symbol)
        if attribute is None:
            continue
        setattr(cuvis_il, attribute, _stub(symbol, attribute))
        if hasattr(low_level, attribute):
            setattr(low_level, attribute, _stub(symbol, attribute))

    cuvis_il.missing_symbols = tuple(missing)
    if missing:
        warnings.warn(
            "cuvis_il: the cuvis library at {} does not export {}. Calling these raises "
            "RuntimeError; everything else works normally."
            .format(_cuvis_library_path, ", ".join(missing)),
            UserWarning, stacklevel=2)
    if unshadowable:
        warnings.warn(
            "cuvis_il: no Python entry point covers {}, so code reaching them cannot be "
            "guarded".format(", ".join(sorted(unshadowable))),
            RuntimeWarning, stacklevel=2)


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


def _hash_from_version(version):
    """The build hash out of a 'CUBERT SDK v. X.Y.Z build: <hash>' string, or ""."""
    found = re.search(r"build:\s*([0-9a-fA-F]+)", version or "")
    return found.group(1) if found else ""


def _record_library_version():
    cuvis_il.built_against_version = _built_against_version()
    cuvis_il.library_path = _cuvis_library_path
    cuvis_il.library_version = _library_version()
    # Both sides are reported in the same form, so the hash that tells two builds of one
    # version apart is parsed the same way out of each. A difference is not a failure,
    # only a fact worth having when something else is wrong, hence no warning.
    cuvis_il.built_against_hash = _hash_from_version(cuvis_il.built_against_version)
    cuvis_il.library_hash = _hash_from_version(cuvis_il.library_version)


_reconcile_with_library()
_record_library_version()

"""Read back what a built extension module expects some other library to provide.

Nothing here lists cuvis function names. They come out of the compiled module itself, so
they cannot fall out of step with what was actually built, which is the whole point: the
extension and the cuvis library are compiled together, but the library deployed on a
user's machine is a separate thing and may not export everything the extension imports.

There is no standard library reader for either format, and the shortcuts do not work.
Deriving the set from the SWIG wrapper's own names instead adds every helper compiled
into the extension, none of which the library exports, so they would all be mistaken for
missing. Only the binary says which name comes from where.
"""
import itertools
import struct
from typing import NamedTuple

_PE_IMPORTS = 1
_PE_DELAY_IMPORTS = 13
_PE32_PLUS = 0x20B

_SHT_DYNSYM = 11
_SHN_UNDEF = 0


def required_cuvis_symbols(module_path, is_wrapped):
    """The cuvis functions the built extension expects the cuvis library to export.

    :param module_path: the compiled extension, ``_cuvis_pyil.pyd`` or ``.so``.
    :param is_wrapped: predicate telling whether a name is one this binding wraps. Only
        consulted for ELF, see below.
    :return: the set of C function names.

    A PE import records which DLL each name comes from, so on Windows the answer is
    exact. ELF undefined symbols do not record a provider, so there the wider set of
    everything the object expects from outside is narrowed by ``is_wrapped``.
    """
    with open(module_path, "rb") as handle:
        data = handle.read()
    if data[:2] == b"MZ":
        return _PortableExecutable(data).imports_from("cuvis")
    return {name for name in _Elf(data).undefined_symbols() if is_wrapped(name)}


def _identity(rva):
    return rva


class _Section(NamedTuple):
    """A PE section header, of which only the address mapping is of interest."""

    virtual_size: int
    rva: int
    raw_size: int
    file_offset: int

    @property
    def size(self):
        # A section holding uninitialised data is larger in memory than on disk, and one
        # padded to the file alignment is larger on disk than in memory.
        return max(self.virtual_size, self.raw_size)

    def contains(self, rva):
        return self.rva <= rva < self.rva + self.size


class _PortableExecutable:
    """Just enough of a PE image to walk its two import tables."""

    def __init__(self, data):
        self._data = data
        coff = struct.unpack_from("<I", data, 0x3C)[0] + 4
        section_count, = struct.unpack_from("<H", data, coff + 2)
        optional_size, = struct.unpack_from("<H", data, coff + 16)
        optional = coff + 20

        self._wide = struct.unpack_from("<H", data, optional)[0] == _PE32_PLUS
        self._image_base, = struct.unpack_from(
            "<Q" if self._wide else "<I", data, optional + 24)

        directory_count, = struct.unpack_from(
            "<I", data, optional + (108 if self._wide else 92))
        directories = optional + (112 if self._wide else 96)
        self._directories = [
            struct.unpack_from("<II", data, directories + 8 * i)[0]
            for i in range(directory_count)]

        headers = optional + optional_size
        self._sections = [
            _Section(*struct.unpack_from("<IIII", data, headers + 40 * i + 8))
            for i in range(section_count)]

    def imports_from(self, prefix):
        """The function names imported from every DLL whose name starts with `prefix`.

        Both tables matter: delay loading moves a DLL's entries out of the ordinary
        import descriptor into the delay one, and cuvis.dll is delay loaded on Windows.
        """
        return set(self._ordinary_imports(prefix)) | set(self._delayed_imports(prefix))

    def _ordinary_imports(self, prefix):
        for lookup, _, _, name, addresses in self._descriptors(_PE_IMPORTS, "<IIIII", 20):
            if self._string(name).lower().startswith(prefix):
                # The lookup table is what the linker wrote; the address table is what
                # the loader overwrites. Bound images keep names only in the former.
                yield from self._imported_names(lookup or addresses, _identity)

    def _delayed_imports(self, prefix):
        for attributes, name, _, _, table in self._descriptors(_PE_DELAY_IMPORTS, "<IIIII", 32):
            # With bit 0 clear the descriptor holds virtual addresses rather than RVAs,
            # as older linkers emitted.
            to_rva = _identity if attributes & 1 else (lambda rva: rva - self._image_base)
            if self._string(to_rva(name)).lower().startswith(prefix):
                yield from self._imported_names(table, to_rva)

    def _descriptors(self, directory, layout, stride):
        """The records of one import directory, which ends at an all zero entry."""
        rva = self._directories[directory] if directory < len(self._directories) else 0
        if not rva:
            return
        for at in itertools.count(self._offset(rva), stride):
            record = struct.unpack_from(layout, self._data, at)
            if not any(record):
                return
            yield record

    def _imported_names(self, rva, to_rva):
        """The names in one thunk table, which ends at a zero entry."""
        word, step = ("<Q", 8) if self._wide else ("<I", 4)
        by_ordinal = 1 << (63 if self._wide else 31)
        for at in itertools.count(self._offset(to_rva(rva)), step):
            entry, = struct.unpack_from(word, self._data, at)
            if not entry:
                return
            if not entry & by_ordinal:      # an ordinal only import carries no name
                yield self._string(to_rva(entry) + 2)   # past the two byte hint

    def _offset(self, rva):
        section = next((s for s in self._sections if s.contains(rva)), None)
        if section is None:
            raise ValueError("rva {:#x} is outside every section".format(rva))
        return section.file_offset + (rva - section.rva)

    def _string(self, rva):
        start = self._offset(rva)
        return self._data[start:self._data.index(b"\0", start)].decode("ascii")


class _SectionHeader(NamedTuple):
    """An ELF section header. The field order is the same at 32 and 64 bit."""

    name: int
    type: int
    flags: int
    address: int
    offset: int
    size: int
    link: int
    info: int
    alignment: int
    entry_size: int


class _Symbol(NamedTuple):
    """The two fields of an ELF symbol that decide whether it is undefined and named."""

    name: int
    section: int


class _Elf:
    """Just enough of an ELF image to list what it expects from elsewhere."""

    def __init__(self, data):
        if data[:4] != b"\x7fELF":
            raise ValueError("not an ELF file")
        self._data = data
        self._wide = data[4] == 2
        endian = "<" if data[5] == 1 else ">"

        if self._wide:
            offset, = struct.unpack_from(endian + "Q", data, 0x28)
            entry_size, count = struct.unpack_from(endian + "HH", data, 0x3A)
            header_layout, self._symbol_layout = endian + "IIQQQQIIQQ", endian + "IBBHQQ"
        else:
            offset, = struct.unpack_from(endian + "I", data, 0x20)
            entry_size, count = struct.unpack_from(endian + "HH", data, 0x2E)
            header_layout, self._symbol_layout = endian + "IIIIIIIIII", endian + "IIIBBH"

        self._headers = [
            _SectionHeader(*struct.unpack_from(header_layout, data, offset + i * entry_size))
            for i in range(count)]

    def undefined_symbols(self):
        """Named symbols the image expects some other object to provide."""
        return {self._string(header.link, symbol.name)
                for header in self._headers if header.type == _SHT_DYNSYM
                for symbol in self._symbols(header)
                if symbol.section == _SHN_UNDEF and symbol.name}

    def _symbols(self, header):
        for at in range(header.offset, header.offset + header.size, header.entry_size):
            fields = struct.unpack_from(self._symbol_layout, self._data, at)
            # Unlike the section header, the symbol field order differs by width: the
            # section index is the fourth field at 64 bit and the sixth at 32.
            yield _Symbol(fields[0], fields[3] if self._wide else fields[5])

    def _string(self, table, offset):
        start = self._headers[table].offset + offset
        end = self._data.index(b"\0", start)
        return self._data[start:end].decode("ascii", "replace")

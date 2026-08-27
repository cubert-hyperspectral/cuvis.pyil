# Detecting cuvis C API signature changes at runtime

Investigation, 2026-08-19.
Question: a cuvis function that exists in both the library the binding was built against and the library actually loaded, but which takes a different number of arguments in each, currently crashes the process.
Can that be detected instead?

Short answer: not from the library, but yes from its version, and a prototype turns the crash into an ordinary Python exception.

## The defect

Diffing `cuvis.h` from `cubertgmbh/cuvis_pyil:3.4.1-ubuntu24.04` against the one from `:3.5.3-ubuntu24.04`, two functions changed arity:

| Function | 3.4.1 | 3.5.3 |
| --- | --- | --- |
| `cuvis_proc_cont_create_from_session_file` | 2 | 3 |
| `cuvis_proc_cont_create_from_mesu` | 2 | 3 |

Both gained `CUVIS_INT i_loadReferences`.
Nothing was removed, and three functions were added.

A third apparent difference, `cuvis_init`, is an artifact of the comparison: `CUVIS_CHAR const *` against `CUVIS_CHAR const*`.
The signature is unchanged.

## Why it crashes rather than misbehaves

The new parameter went in the middle of the list, so the arguments shift rather than one being ignored at the end.

`cuvis/ProcessingContext.py:33` calls, through the binding:

```
cuvis_proc_cont_create_from_session_file(session_handle, 1, out_pointer)
```

A 3.4.1 library reads that as `(i_sess, o_pProcCont)`.
Its output pointer is therefore the literal `1`, and it writes a handle to address `0x1`.

That is a wild write, not a bad return value, which is why the failure is a segmentation fault with no exception and no usable traceback:

```
Fatal Python error: Segmentation fault
  File "cuvis_il/cuvis_il.py", line 2298 in cuvis_proc_cont_create_from_session_file
  File "cuvis/ProcessingContext.py", line 33 in __init__
```

The existing protection does not help.
`cuvis_il/__init__.py` detects functions the loaded library does not export and replaces them with stubs that raise.
Here the symbol is present and resolves perfectly well.
It is simply a different function than the one the binding was compiled to call.

## Why the library cannot be asked

Three independent ways to recover a signature from a shared object, all checked against the shipped `libcuvis.so`, all negative.

**The symbols carry no type information.**
The cuvis C API is `extern "C"`, so its symbols are undecorated:

```
$ nm -D --defined-only /lib/cuvis/libcuvis.so | grep cuvis_proc_cont_create_from_session_file
0000000000430310 T cuvis_proc_cont_create_from_session_file
```

A name and an address.
No arity, no parameter types.
For contrast, the C++ symbols in the same library are mangled and do encode their full parameter lists, but the C entry points we call are not among them.

**There is no debug information.**
`readelf -S` finds no `.debug_info` section.
The library is stripped, so there is no DWARF to read parameter counts from.

**cuvis does not version its own symbols.**
`readelf -V` shows a populated `.gnu.version` section, but every entry belongs to an imported glibc or libstdc++ symbol.
`cuvis_init` and its siblings are plain `GLOBAL DEFAULT`.

That last point is the important one.
ELF symbol versioning is the standard mechanism for exactly this problem, and it is what glibc uses.
Had the cuvis symbols been version-tagged, the dynamic loader itself would have refused to bind the changed function and the process would have failed at load time with a clear message, instead of corrupting memory at call time.

So there is no way to ask a loaded cuvis library what shape its functions are.

## What can be known

The loaded library reports its own version, and the binding already reads both sides.
`cuvis_built_against_version()` returns the banner of the library the binding was compiled against, and `cuvis_version()` returns the banner of the one loaded next to it.
Both are already surfaced as `built_against_version` and `library_version`.

That is enough, because the arities are knowable at build time even though they are not knowable at run time.
Parsing the `cuvis.h` being compiled against yields `{function: arity}` for that release.
Doing the same once per released SDK gives a table that the loaded version selects from.

## Prototype

Three parts, all small.

1. A generator that reads one `cuvis.h` and emits `{function: arity}` as JSON.
   Declarations wrap across lines, so it flattens the text and strips comments before matching, rather than scanning line by line.
2. `cuvis_il/_signatures.py`, which parses the `X.Y.Z` out of each banner, loads the table for each, and returns the functions whose arities disagree.
   When either release has no table it returns that fact rather than an empty result, because "checked and found nothing" and "could not check" must not look alike to the caller.
3. Four lines in `cuvis_il/__init__.py` that feed those names into the existing `_shadow` path.

The third point is why this is cheap.
The machinery that replaces a function with a raising stub already exists for missing symbols.
A signature mismatch is the same remedy for a different reason, so it reuses the same code and the same published surface, alongside `missing_symbols`.

### Results

Both directions were measured in the cuvis.docker images.

| Binding | Library | Before | After |
| --- | --- | --- | --- |
| 3.5.3 | 3.4.1 | segmentation fault, exit 139 | `RuntimeError`, exit 1 |
| 3.5.3 | 3.5.3 | 134 tests pass | 134 tests pass, no warnings, empty flags |

The mismatch now reports itself at import:

```
UserWarning: cuvis_il: the cuvis library at /lib/cuvis/libcuvis.so declares
cuvis_proc_cont_create_from_mesu, cuvis_proc_cont_create_from_session_file differently
from the library this binding was built against. Calling these raises RuntimeError;
everything else works normally.
```

and at the call:

```
RuntimeError: cuvis: 'cuvis_proc_cont_create_from_session_file' is not usable with the
cuvis library loaded from /lib/cuvis/libcuvis.so. That library is not the one this
binding was built against (built against: CUBERT SDK v. 3.5.3 build: 0f416fb6...;
loaded: CUBERT SDK v. 3.4.1 build: d20de35f...).
```

The matched-pair control matters as much as the catch.
A checker that fires on healthy installations is worse than no checker, because people learn to ignore it.

## Limitations

**It only knows releases it ships a table for.**
Against an unfamiliar version it warns that checking was not possible and proceeds, which is the correct failure mode but is still a gap.
That means one generated table per release, forever, and a release that forgets to add one silently loses the protection.

**It compares arity, not types.**
A parameter changing from `CUVIS_INT` to `CUVIS_SIZE`, or a pointer changing what it points at, keeps the same count and passes the check.
Extending the comparison to the normalised parameter type strings is straightforward with the same generator and would close most of that gap.

**It cannot cover the first call.**
The check runs at import, before anything is called, which is the right place.
But it depends on `cuvis_version()` itself being callable, and that function's signature has never changed.
If it ever did, the check would crash on the way to protecting anything.

## Recommendations

### For the wrapper, now

Ship the version-keyed arity manifest described above.
It is roughly one new module, one build step, and four lines in the existing loader, and it converts this entire class of failure from a memory-corrupting crash into a message that names the two libraries.

### For the SDK, properly

**Rename the symbol whenever its signature changes in a breaking way.**
Had 3.5 exported `cuvis_proc_cont_create_from_session_file_v2` rather than redefining the existing name, the wrapper's existing missing-symbol detection would have caught this with no new machinery at all: the symbol is absent, it gets shadowed, the caller gets a `RuntimeError`.
No manifest, no table to maintain per release, no build step, and it protects the C++, C# and any future binding rather than only Python.

ELF symbol versioning achieves the same on Linux and is more idiomatic there, but it has no Windows equivalent, so a rename is the portable answer.

Failing that, a `cuvis_abi_version()` returning an integer bumped on any breaking C API change would let a binding refuse to run at all, which is cruder but far better than the present behaviour.

This belongs in a cuvis.c ticket.
It is not a Python problem, and every language binding is exposed to it.

## Reproducing

```bash
# the signature diff
docker run --rm -v "$PWD:/out" cubertgmbh/cuvis_pyil:3.4.1-ubuntu24.04 \
  cp /usr/include/cuvis.h /out/cuvis_341.h
docker run --rm -v "$PWD:/out" cubertgmbh/cuvis_pyil:3.5.3-ubuntu24.04 \
  cp /usr/include/cuvis.h /out/cuvis_353.h
python sigdiff.py cuvis_341.h cuvis_353.h

# what the library does and does not expose
docker run --rm cubertgmbh/cuvis_pyil:3.4.1-ubuntu24.04 bash -lc '
  nm -D --defined-only /lib/cuvis/libcuvis.so | grep cuvis_proc_cont_create_from_session_file
  readelf -S /lib/cuvis/libcuvis.so | grep -c debug_info
  readelf --dyn-syms /lib/cuvis/libcuvis.so | grep cuvis_init'
```

The crash itself needs a binding built in the 3.5.3 image and run in the 3.4.1 one.
Note that this pairing is also how the unrelated missing-symbol path is exercised: 3.4.1 does not export the three `cuvis_acq_cont_dead_pixel_correction_*` functions, and those are already handled correctly today.

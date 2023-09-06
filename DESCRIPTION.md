# Python Bindings for the Cuvis SDK

This package contains compiled versions of the python bindings used by the [Cuvis Python Wrapper](https://github.com/cubert-hyperspectral/cuvis.python).
Next to installing this package, you need to install the Cuvis C SDK (see [here]( https://cloud.cubert-gmbh.de/index.php/s/kKVtx0x2fmYqVgx)).
The source code for building this package can be found [here](https://github.com/cubert-hyperspectral/cuvis.pyil).

## Supported Versions

### NumPy 

This package is compiled against the ABI of NumPy 1.22. Because of the [backwards compatibility](https://numpy.org/doc/stable/dev/depending_on_numpy.html) of the NumPy ABI,
this package works therefore with NumPy versions >=1.22.0.

### Python

For each major version the python bindings need to be seperately compiled against the python headers.
We provide binaries for Python 3.9, 3.10 and 3.11 in this package.

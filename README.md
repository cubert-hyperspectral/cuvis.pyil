# Cuvis python interface layer (required for using the python wrapper)

## Building
For building the python interface layer *cuvis_pyil*, first clone this git repository and initialize it's submodules recursively

```
git submodule update --init --recursive
```

Next, you need to install the Cuvis C SDK (see https://cloud.cubert-gmbh.de/index.php/s/kKVtx0x2fmYqVgx).

For building the python stubs for wrapping between C libraries and python, you'll need SWIG (see https://www.swig.org/download.html).

Next make sure that your preferred version of numpy is installed. See [here](#dependency-to-numpy)

Then use CMake (see https://cmake.org/download/) to configure and generate your project. CMake will require you to locate the Cuvis C SDK (this should be found automatically, if the Cuvis C SDK is properly installed. Also, you need to point the variable *SWIG_EXECUTABLE* to the path of the *swig.exe*

## Dependency to numpy
The python interface layer is dependent on numpy. Specifically, this means that we need the c headers of the numpy library.
To compile the python interface layer install your preferred version of numpy. For example
```
pip install numpy
```
CMake will try to find the numpy path via the `np.get_include` function.
If this does not work on your machine simply set the `Cuvis_NUMPY_PATH` variable with the return of this function by hand.
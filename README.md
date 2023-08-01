# Cuvis python interface layer (required for using the python wrapper)

## Building
For building the python interface layer *cuvis_pyil*, first clone this git repository and initialize it's submodules recursively

```
git submodule update --init --recursive
```

Next, you need to install the Cuvis C SDK (see https://cloud.cubert-gmbh.de/index.php/s/kKVtx0x2fmYqVgx).

For building the python stubs for wrapping between C libraries and python, you'll need SWIG (see https://www.swig.org/download.html).

Then use CMake (see https://cmake.org/download/) to configure and generate your project. CMake will require you to locate the Cuvis C SDK (this should be found automatically, if the Cuvis C SDK is properly installed. Also, you need to point the variable *SWIG_EXECUTABLE* to the path of the *swig.exe*

## Dependency to numpy
Currently numpy for python 3.9 is included into this repository. As such, the *cuvis_pyil* will only work with python 3.9. This can be fixed, by chaning the Numpy dependencies in this project.
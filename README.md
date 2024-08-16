![image](https://raw.githubusercontent.com/cubert-hyperspectral/cuvis.sdk/main/branding/logo/banner.png)

# cuvis.pyil (python interface layer; required for using the python wrapper)

cuvis.pyil is the python interface binding for the Cuvis SDK written in C ([available here](https://github.com/cubert-hyperspectral/cuvis.sdk)).

- **Website:** https://www.cubert-hyperspectral.com/
- **Source code:** https://github.com/cubert-hyperspectral/
- **Support:** http://support.cubert-hyperspectral.com/

For other supported program languages, please have a look at the source code page.

## Installation

### Prerequisites

First, you need to install the Cuvis C SDK from [here](https://cloud.cubert-gmbh.de/s/qpxkyWkycrmBK9m).
The installation registers the installation path in the environment, which the python interface layer is linked to.

:warning: **If the C SDK is reinstalled into another directory later on, the linkage breaks and the python wrapper might stop working.**


### Via pip

If you wish to use cuvis-il within another project, from within your 
project environment, run 

```shell
pip install cuvis-il
```
or add `cuvis-il` to your project `requirements.txt` or `setup.py`.
We currently provide pre-compiled binaries for Python 3.9, 3.10, 3.11 and 3.12 for Windows 64-bit.

### Via repository

If you wish to download and use cuvis locally, clone the git repository

  ```shell
  git clone git@github.com:cubert-hyperspectral/cuvis.pyil.git
  ```
and then initialize the submodules.

```
git submodule update --init --recursive
```

For building the python stubs for wrapping between C libraries and python, you'll need SWIG (see https://www.swig.org/download.html).

Next make sure that your preferred version of [NumPy](https://pypi.org/project/numpy/) is manually pre-installed in your go-to environment. See [here](#dependency-to-numpy).

Then use CMake (see https://cmake.org/download/) to configure and generate your project. CMake will require you to locate the Cuvis C SDK (this should be found automatically, if the Cuvis C SDK is properly installed). 
Also, you need to point the variable *SWIG_EXECUTABLE* to the path of the *swig.exe*.

This project will then generate the `_cuvis_pyil.pyd` and `cuvis_il.py` files needed for running the Cuvis Python SDK wrapper. 

:warning: **You might also use the `cuvis_il.py` directly, which provides all functionalities as single methods without organization into objects. Support for code without the additional [wrapper](https://github.com/cubert-hyperspectral/cuvis.python) is limited, though.**

#### Dependency to NumPy

The python interface layer is dependent on [NumPy](https://pypi.org/project/numpy/). Specifically, this means that we need the C headers of the NumPy library.
Notice that NumPy has [backwards compatibility](https://numpy.org/doc/stable/dev/depending_on_numpy.html).
To compile the python interface layer install your preferred version of NumPy. For example the newest stable release via

```
pip install numpy
```

CMake will try to find the NumPy path using the `find_package(Python REQUIRED COMPONENTS Interpreter Development NumPy)`.
To support the usage of a virtual environment, set the `Python_ROOT_DIR` variable to the directory containing your virtual environment.

Our pre-compiled binaries are compiled with 1.22 (Python 3.9 and 3.10), 1.23 (Python 3.11) and 1.26 (Python 3.12).

### Getting involved

cuvis.hub welcomes your enthusiasm and expertise!

With providing our SDK wrappers on GitHub, we aim for a community-driven open 
source application development by a diverse group of contributors.
Cubert GmbH aims for creating an open, inclusive, and positive community.
Feel free to branch/fork this repository for later merge requests, open 
issues or point us to your application specific projects.
Contact us, if you want your open source project to be included and shared 
on this hub; either if you search for direct support, collaborators or any 
other input or simply want your project being used by this community.
We ourselves try to expand the code base with further more specific 
applications using our wrappers to provide starting points for research 
projects, embedders or other users.

### Getting help

Directly code related issues can be posted here on the GitHub page, other, more 
general and application related issues should be directed to the 
aforementioned Cubert GmbH [support page](http://support.cubert-hyperspectral.com/).

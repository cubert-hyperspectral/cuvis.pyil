#!/bin/bash
set -e

# Usage: build_and_upload_single.sh -p <python_path> -n <numpy_version> -b <build_dir> -t <pip_token>

CMAKE_PATH="C:/Program Files/CMake/bin/cmake.exe"
SWIG_PATH="C:/Program Files/swigwin-4.0.2"


while getopts "p:n:b:t:" opt; do
    case ${opt} in
        p) PYTHON_PATH="$OPTARG" ;;
        n) NUMPY_VERSION="$OPTARG" ;;
        b) BUILD_DIR="$OPTARG" ;;
        t) PIP_TOKEN="$OPTARG" ;;
        \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
    esac
done

if [[ -z "$PYTHON_PATH" || -z "$NUMPY_VERSION" || -z "$BUILD_DIR" || -z "$CMAKE_PATH" || -z "$PIP_TOKEN" ]]; then
    echo "Usage: $0 -p <python_path> -n <numpy_version> -b <build_dir>  -t <pip_token>"
    exit 1
fi

echo "Building for Python at: $PYTHON_PATH"
echo "Using NumPy version: $NUMPY_VERSION"
echo "Build directory: $BUILD_DIR"
echo "CMake path: $CMAKE_PATH"

# Extract version short name
relative=$(basename "$PYTHON_PATH")
version_short="${relative//[^0-9]/}"

echo -e "\t...Setting up Python environment"
rm -rf venv_$relative
rm -rf $BUILD_DIR

"$PYTHON_PATH/python.exe" -m venv "venv_$relative"
source "venv_$relative/Scripts/activate"

echo -e "\t...Update pip"
python -m ensurepip --upgrade
python -m pip install --upgrade pip
echo -e "\t...Updating build packages"
pip install -U setuptools wheel build twine -qq

echo -e "\t...Installing NumPy"
pip install numpy=="$NUMPY_VERSION" -qq

echo -e "\t...Executing CMake"
python_dir="$(pwd)/venv_$relative"
"$CMAKE_PATH" -DCMAKE_BUILD_TYPE=Release \
             -DDOXYGEN_BUILD_DOCUMENTATION=FALSE \
             -DSWIG_DIR="$SWIG_PATH/Lib" \
             -DSWIG_EXECUTABLE="$SWIG_PATH/swig.exe" \
             -DPython_ROOT_DIR="$python_dir" \
             -B "$BUILD_DIR" .

"$CMAKE_PATH" --build "$BUILD_DIR" --target cuvis_pyil --config Release

rm -rf ./cuvis_il/*cuvis*
rm -rf ./dist/*.whl

chmod +x ./copy_pyil_files.sh
./copy_pyil_files.sh  "$BUILD_DIR"

echo -e "\t...Packing Python files"
echo -e "\t...Version $version_short"

python -m build --wheel --no-isolation
wheel_file=$(find dist -type f -name "*.whl")
echo "Found $wheel_file"

python -m wheel tags --remove --python-tag=py$version_short --platform-tag=win_amd64 "$wheel_file"

echo -e "\t...Uploading to TestPyPI"
twine upload dist/*.whl --password="$PIP_TOKEN" --username="__token__"

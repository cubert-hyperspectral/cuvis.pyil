#!/bin/bash

# Usage: build_and_upload_single.sh -v <python_version> -p <platform_tag> -n <numpy_version> -b <build_dir> -t <pip_token>

while getopts "v:p:n:b:t:" opt; do
    case ${opt} in
        v) PYTHON_PATH="$OPTARG" ;;
		p) PLATFORM_TAG="$OPTARG" ;;
        n) NUMPY_VERSION="$OPTARG" ;;
        b) BUILD_DIR="$OPTARG" ;;
        t) PIP_TOKEN="$OPTARG" ;;
        \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
    esac
done

if [[ -z "$PYTHON_PATH" || -z "$PLATFORM_TAG" || -z "$NUMPY_VERSION" || -z "$BUILD_DIR" || -z "$PIP_TOKEN" ]]; then
    echo "Usage: $0 -p <python_path> -p <platform_tag> -n <numpy_version> -b <build_dir>  -t <pip_token>"
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
rm -rf /tmp/venv_$relative
rm -rf $BUILD_DIR

$PYTHON_PATH -m venv "/tmp/venv_$relative"
source "venv_$relative/bin/activate"

echo -e "\t...Update pip"
$PYTHON_PATH -m ensurepip --upgrade
$PYTHON_PATH -m pip install --upgrade pip
echo -e "\t...Updating build packages"
$PYTHON_PATH -m pip install -U setuptools wheel build twine -qq

echo -e "\t...Installing NumPy"
$PYTHON_PATH -m pip install numpy=="$NUMPY_VERSION" -qq

echo -e "\t...Executing CMake"

cmake -DCMAKE_BUILD_TYPE=Release \
             -DDOXYGEN_BUILD_DOCUMENTATION=FALSE \
             -DPython_ROOT_DIR="/tmp/venv_$relative" \
             -B "$BUILD_DIR" .

cmake --build "$BUILD_DIR" --target cuvis_pyil --config Release

rm -rf ./cuvis_il/*cuvis*
rm -rf ./dist/*.whl

./copy_pyil_files.sh  "$BUILD_DIR/Release"

echo -e "\t...Packing Python files"
echo -e "\t...Version $version_short"

$PYTHON_PATH -m build --wheel --no-isolation
wheel_file=$(find dist -type f -name "*.whl")
echo "Found $wheel_file"

$PYTHON_PATH -m wheel tags --remove --python-tag=py$version_short --platform-tag=$PLATFORM_TAG "$wheel_file"

echo -e "\t...Uploading to TestPyPI"
twine upload dist/*.whl -r testpypi --password="$PIP_TOKEN" --username="__token__"

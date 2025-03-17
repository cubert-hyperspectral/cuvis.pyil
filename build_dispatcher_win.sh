#!/bin/bash

# CHANGE ME
SEARCH_PATH="C:/Users/$USERNAME/AppData/Local/Programs/Python"

# CHANGE ME
BUILD_DIR="C:/dev/builds"

#!/bin/bash

# Usage: build_dispatcher.sh -s <search_path> -b <builds_dir>

# Default numpy versions based on Python versions
declare -A NUMPY_VERSIONS=(
    ["Python39"]="1.22.0"
    ["Python310"]="1.22.0"
    ["Python311"]="1.23.0"
    ["Python312"]="1.26.0"
    ["Python313"]="2.0.0"
)

read -s -p "Enter pip token:" PIP_TOKEN  


echo "Searching Python installations in: $SEARCH_PATH"
echo "Build directory: $BUILD_DIR"
echo "Using CMake: $CMAKE_PATH"

# Find all subdirectories in search path
subfolders=$(find "$SEARCH_PATH" -maxdepth 1 -type d)

for folder in $subfolders; do
    relative=$(realpath --relative-to="$SEARCH_PATH" "$folder")
    
    if [[ "$relative" != "." ]]; then
        echo "Processing Python version: $relative"

        # Determine the correct NumPy version
        numpy_version="${NUMPY_VERSIONS[$relative]:-1.22.0}"  # Default if not listed

        # Define build output directory
        build_subdir="$BUILD_DIR/cuvis_pyil_$relative"

        # Call the inner script
        ./build_and_upload_win.sh -p "$folder" -n "$numpy_version" -b "$build_subdir" -t "$PIP_TOKEN"
    fi
done

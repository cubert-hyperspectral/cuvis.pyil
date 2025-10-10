#!/bin/bash

# CHANGE ME
SEARCH_PATH="C:/Users/$USERNAME/AppData/Local/Programs/Python"

# CHANGE ME
BUILD_DIR="C:/dev/builds"

#!/bin/bash

# Usage: build_dispatcher.sh -s <search_path> -b <builds_dir>

# Default numpy versions based on Python versions
declare -A NUMPY_VERSIONS=(
    ["Python39"]="2.0.0"
    ["Python310"]="2.0.0"
    ["Python311"]="2.0.0"
    ["Python312"]="2.0.0"
    ["Python313"]="2.0.0"
	["Python314"]="2.0.0"
)

read -s -p "Enter pip token:" PIP_TOKEN  


echo "Searching Python installations in: $SEARCH_PATH"
echo "Build directory: $BUILD_DIR"
echo "Using CMake: $CMAKE_PATH"

# Find all subdirectories in search path
declare -A rel2abs
rel_names=()
for folder in $(find "$SEARCH_PATH" -maxdepth 1 -type d 2>/dev/null); do
  rel=$(realpath --relative-to="$SEARCH_PATH" "$folder")
  [[ "$rel" == "." ]] && continue
  rel_names+=("$rel")
  rel2abs["$rel"]="$folder"
done

# fancy multi-select
mapfile -t chosen < <(printf '%s\n' "${rel_names[@]}" | fzf -m --prompt="Select Pythons > " \
  --header="Tab to select multiple, Enter to confirm")

for relative in "${chosen[@]}"; do
    
    echo "Processing Python version: $relative"

    folder="${rel2abs[$relative]}"
    numpy_version="${NUMPY_VERSIONS[$relative]:-1.22.0}"
    build_subdir="$BUILD_DIR/cuvis_pyil_$relative"

    ./build_and_upload_win.sh -p "$folder" -n "$numpy_version" -b "$build_subdir" -t "$PIP_TOKEN"
done

#!/bin/bash
set -e  # Exit on any error

# Ensure a binary directory argument is provided
if [[ $# -ne 1 ]]; then
    echo "Usage: bash copy_pyil_files.sh <binary_directory>"
    exit 1
fi

BINARY_DIR="$1"

# Determine script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Validate the binary directory
if [[ ! -d "$BINARY_DIR" ]]; then
    echo "Error: Binary directory $BINARY_DIR does not exist!"
    exit 1
fi

echo "Using binary directory: $BINARY_DIR"

# Determine platform-specific filenames
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    FILES=("_cuvis_pyil.so" "cuvis_il.py")
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    FILES=("_cuvis_pyil.pyd" "cuvis_il.py")
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

# Copy the necessary files
for FILE in "${FILES[@]}"; do
    if [[ -f "$BINARY_DIR/$FILE" ]]; then
        cp "$BINARY_DIR/$FILE" "$SCRIPT_DIR/cuvis_il/" || {
            echo "Error copying $FILE"
            exit 1
        }
        echo "Copied $FILE to cuvis_il/"
    else
        echo "Warning: $FILE not found in $BINARY_DIR"
    fi
done

echo "PyIL files copied successfully."

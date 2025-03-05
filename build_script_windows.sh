#!/bin/bash

numpy_version="1.22.0"

# CHANGE ME
search_path="path/to/python/installations e.g. AppData/local/programs"

# CHANGE ME
main_builds_dir="path/to/builds/dir"

# CHANGE ME
cmake="path/to/cmake"

subfolders=$(find "$search_path" -maxdepth 1 -type d)

read -p "pip username:" username 
read -s -p "pip password:" password  

echo ""

for folder in $subfolders; do
	relative=$(realpath --relative-to="$search_path" "$folder")
	if [[ "$relative" != "." ]]; then
		echo "Building Python binaries with $relative..."
		
		case $relative in
			Python39 | Python310)
			numpy_version="1.22.0"
			;;
			Python311)
			numpy_version="1.23.0"
			;;
			Python312 | Python313)
			numpy_version="1.26.0"
			;;
		esac
		
		echo -e "\t...setting up python environment"
		rm -rf "venv_$relative"
		rm -rf "$main_builds_dir/cuvis_pyil_$relative"
		$folder/python.exe -m venv "venv_$relative"
		source venv_$relative/Scripts/activate
		pip install wheel --upgrade -qq
		pip install setuptools -qq
		pip install twine -qq
		pip install numpy=="$numpy_version" -qq
		
		echo -e "\t...executing cmake"
		python_dir="$(pwd)/venv_$relative"
		"$cmake" -DCMAKE_BUILD_TYPE=Release -DDOXYGEN_BUILD_DOCUMENTATION=FALSE -DPython_ROOT_DIR="$python_dir" -B "$main_builds_dir\cuvis_pyil_$relative" .
		"$cmake" --build "$main_builds_dir/cuvis_pyil_$relative" --target cuvis_pyil --config Release
		
		echo -e "\t...packing python files"
		CUVIS_NUMPY_COMPILED=$numpy_version python setup.py upload --password=$password --username=$username
		#break
	fi
done
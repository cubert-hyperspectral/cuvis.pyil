#!/bin/bash

numpy_version="1.22.0"

# CHANGE ME
search_path="/usr/bin"

# CHANGE ME
main_builds_dir="/tmp"

subfolders=$(find "$search_path" -maxdepth 1 -name '*python*')

read -p "pip username:" username 
read -s -p "pip password:" password  

echo ""

for folder in $subfolders; do
	relative=$(realpath --relative-to="$search_path" "$folder")
	if [[ "$relative" != "." ]]; then
		echo "Building Python binaries with $relative..."
		
		case $relative in
			python3.9 | python3.10)
			numpy_version="1.22.0"
			;;
			python3.11)
			numpy_version="1.23.0"
			;;
			python3.12)
			numpy_version="1.26.0"
			;;
		esac
		
		echo -e "\t...setting up python environment"
		rm -rf "venv_$relative"
		rm -rf "$main_builds_dir/cuvis_pyil_$relative"
		$relative -m venv "venv_$relative"
		source venv_$relative/bin/activate
		$relative -m pip install wheel --upgrade -qq
		$relative -m pip install setuptools -qq
		$relative -m pip install twine -qq
		$relative -m pip install auditwheel -qq
		$relative -m pip install numpy=="$numpy_version" -qq
		
		echo -e "\t...executing cmake"
		python_dir="$(pwd)/venv_$relative"
		cmake -DCMAKE_BUILD_TYPE=Release -DDOXYGEN_BUILD_DOCUMENTATION=FALSE -DPython_ROOT_DIR="$python_dir" -B "$main_builds_dir\cuvis_pyil_$relative" .
		cmake --build "$main_builds_dir/cuvis_pyil_$relative" --target cuvis_pyil --config Release
		
		echo -e "\t...packing python files"
		CUVIS_NUMPY_COMPILED=$numpy_version $relative setup.py upload --password=$password --username=$username
	fi
done
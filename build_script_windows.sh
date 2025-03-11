#!/bin/bash

numpy_version="1.22.0"

# CHANGE ME
search_path="C:/Users/simon.birkholz/AppData/Local/Programs/Python"

# CHANGE ME
main_builds_dir="C:/dev/builds"

# CHANGE ME
cmake="C:/Program Files/CMake/bin/cmake.exe"

subfolders=$(find "$search_path" -maxdepth 1 -type d)

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
			python3.13)
			numpy_version="2.0.0"
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
		"$cmake" -DCMAKE_BUILD_TYPE=Release -DDOXYGEN_BUILD_DOCUMENTATION=FALSE -DSWIG_DIR="C:\Program Files\swigwin-4.0.2\Lib" -DSWIG_EXECUTABLE="C:\Program Files\swigwin-4.0.2\swig.exe" -DPython_ROOT_DIR="$python_dir" -B "$main_builds_dir\cuvis_pyil_$relative" .
		"$cmake" --build "$main_builds_dir/cuvis_pyil_$relative" --target cuvis_pyil --config Release
		
		echo -e "\t...packing python files"
		CUVIS_NUMPY_COMPILED=$numpy_version python setup.py upload --password=$password --username=$username
		#break
	fi
done
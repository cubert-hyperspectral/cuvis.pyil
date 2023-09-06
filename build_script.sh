#!/bin/bash

numpy_version="1.22.0"

search_path="path/to/python/installations e.g. AppData/local/programs"

cmake="C:\Program Files\CMake\bin\cmake.exe"

subfolders=$(find "$search_path" -maxdepth 1 -type d)

read -p "pip username:" username 
read -s -p "pip password:" password  

echo ""

for folder in $subfolders; do
	relative=$(realpath --relative-to="$search_path" "$folder")
	if [[ "$relative" != "." ]]; then
		echo "Building Python binaries with $relative..."
		
		echo -e "\t...setting up python environment"
		rm -rf "venv_$relative"
		$folder/python.exe -m venv "venv_$relative"
		source venv_$relative/Scripts/activate
		pip install wheel --upgrade -qq
		pip install twine -qq
		pip install numpy=="1.22.0" -qq
		
		echo -e "\t...executing cmake"
		python_dir="$(pwd)/venv_$relative"
		"$cmake" -DCMAKE_BUILD_TYPE=Release -DDOXYGEN_BUILD_DOCUMENTATION=FALSE -DPython_ROOT_DIR="$python_dir" -B "C:\dev\builds\cuvis_pyil_$relative" .
		"$cmake" --build "C:\dev\builds\cuvis_pyil_$relative" --target cuvis_pyil --config Release
		
		echo -e "\t...packing python files"
		python setup.py upload --password=$password --username=$username
		#break
	fi
done
cmake_minimum_required(VERSION 3.20.0)
PROJECT(cuvis_pyil C CXX)

set(target_name cuvis_pyil)
set(SWIG_LANGUAGE python)

file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/intermediate/${target_name}")
set(SWIG_OUTPUT_DIR "${CMAKE_BINARY_DIR}/intermediate/${target_name}")

set(CMAKE_SWIG_FLAGS "-doxygen")

list(APPEND CMAKE_MODULE_PATH
  "${CMAKE_CURRENT_LIST_DIR}/cuvis.swig/")
include(cuvis_swig)

set(Python_ROOT_DIR "${Python_ROOT_DIR}" CACHE PATH "Path Hint to the Python Directory")
# FIND_PACKAGE(PythonLibs REQUIRED)
find_package(Python REQUIRED COMPONENTS Interpreter Development NumPy)

file(WRITE numpy_version.stamp ${Python_NumPy_VERSION})
file(WRITE python_version.stamp ${Python_VERSION})
message("python version ${Python_VERSION}")
message("numpy version ${Python_NumPy_VERSION}")

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/${Python_VERSION}")

target_include_directories(${target_name} PUBLIC ${Python_INCLUDE_DIRS} )
if(WIN32 OR UNIX)

target_include_directories(${target_name} PUBLIC "${Python_NumPy_INCLUDE_DIRS}" )
endif()
#message(${PYTHON_LIBRARIES})
target_link_libraries(${target_name} PRIVATE ${Python_LIBRARIES})

add_custom_command(TARGET ${target_name} POST_BUILD COMMAND ${CMAKE_COMMAND} -E copy "${SWIG_OUTPUT_DIR}/cuvis_il.py"  $<TARGET_FILE_DIR:${target_name}> )

# write where to find the compiled library 
add_custom_command(TARGET ${target_name} POST_BUILD COMMAND ${CMAKE_COMMAND} -E echo "$<TARGET_FILE_DIR:${target_name}>" > "${CMAKE_CURRENT_SOURCE_DIR}/binary_dir_${Python_VERSION}.stamp" )

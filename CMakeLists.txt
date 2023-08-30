cmake_minimum_required(VERSION 3.20.0)
PROJECT(cuvis_pyil C CXX)

set(target_name cuvis_pyil)
set(SWIG_LANGUAGE python)

file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/intermediate/${target_name}")
set(SWIG_OUTPUT_DIR "${CMAKE_BINARY_DIR}/intermediate/${target_name}")

list(APPEND CMAKE_MODULE_PATH
  "${CMAKE_CURRENT_LIST_DIR}/cuvis.swig/")
include(cuvis_swig)


FIND_PACKAGE(PythonLibs REQUIRED)


target_include_directories(${target_name} PUBLIC ${PYTHON_INCLUDE_DIR} )
if(WIN32)
#target_include_directories(${target_name} PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include_win32_3.9" )

execute_process(COMMAND CMD /c python ${CMAKE_CURRENT_SOURCE_DIR}/numpy/find_numpy.py OUTPUT_VARIABLE numpy_path)
if("${numpy_path}" STREQUAL "no numpy")
	message(FATAL_ERROR "numpy seems to be not installed" )
endif()
#message("${numpy_path}")
set(Cuvis_NUMPY_PATH "${numpy_path}" CACHE PATH "")
target_include_directories(${target_name} PUBLIC "${Cuvis_NUMPY_PATH}" )
endif()
#message(${PYTHON_LIBRARIES})
target_link_libraries(${target_name} PRIVATE ${PYTHON_LIBRARY})

add_custom_command(TARGET ${target_name} POST_BUILD COMMAND ${CMAKE_COMMAND} -E copy "${SWIG_OUTPUT_DIR}/cuvis_il.py"  $<TARGET_FILE_DIR:${target_name}> )
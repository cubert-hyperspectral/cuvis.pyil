cmake_minimum_required(VERSION 3.20.0)
PROJECT(cuvis_pyil C CXX)

set(target_name cuvis_pyil)
set(SWIG_LANGUAGE python)

set(SWIG_OUTPUT_DIR "${EXECUTABLE_OUTPUT_PATH}/intermediate/${target_name}")

list(APPEND CMAKE_MODULE_PATH
  "${CMAKE_CURRENT_LIST_DIR}/cuvis.swig/")
include(cuvis_swig)


FIND_PACKAGE(PythonLibs REQUIRED)


target_include_directories(${target_name} PUBLIC ${PYTHON_INCLUDE_DIR} )
if(WIN32)
target_include_directories(${target_name} PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include_win32_3.9" )
endif()
#message(${PYTHON_LIBRARIES})
target_link_libraries(${target_name} PRIVATE ${PYTHON_LIBRARY})

add_custom_command(TARGET ${target_name} POST_BUILD COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:${target_name}> ${SWIG_OUTPUT_DIR} )
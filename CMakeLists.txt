cmake_minimum_required(VERSION 3.20.0)
PROJECT(cuvis_pyil C CXX)

set(target_name cuvis_pyil)
set(SWIG_LANGUAGE python)

file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/intermediate/${target_name}")
set(SWIG_OUTPUT_DIR "${CMAKE_BINARY_DIR}/intermediate/${target_name}")


list(APPEND CMAKE_MODULE_PATH
  "${CMAKE_CURRENT_LIST_DIR}/cuvis.swig/")
include(cuvis_swig)

set(Python_ROOT_DIR "${Python_ROOT_DIR}" CACHE PATH "Path Hint to the Python Directory")
# FIND_PACKAGE(PythonLibs REQUIRED)
find_package(Python REQUIRED COMPONENTS Interpreter Development NumPy)

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/${Python_VERSION}")

target_include_directories(${target_name} PUBLIC ${Python_INCLUDE_DIRS} )
if(WIN32 OR UNIX)

target_include_directories(${target_name} PUBLIC "${Python_NumPy_INCLUDE_DIRS}" )
endif()
#message(${PYTHON_LIBRARIES})
target_link_libraries(${target_name} PRIVATE ${Python_LIBRARIES})

set_property(TARGET ${target_name} PROPERTY SWIG_COMPILE_OPTIONS -doxygen)

# The version of the cuvis library this binding is compiled against, reported at
# import time so a mismatch with the deployed library is visible rather than silent.
target_compile_definitions(${target_name} PRIVATE CUVIS_BINDING_BUILT_VERSION="${Cuvis_VERSION}")

if(MSVC)
  # Delay-load cuvis.dll so a symbol missing from the deployed library no longer
  # breaks `import cuvis_il`; the failure moves to the call, where the SEH guard in
  # cuvis_il.i turns it into a Python exception.
  target_link_options(${target_name} PRIVATE "/DELAYLOAD:cuvis.dll")
  target_link_libraries(${target_name} PRIVATE delayimp)

elseif(UNIX)
  # Lazy binding, so an outdated libcuvis.so that is missing a symbol does not fail
  # the import; cuvis_il/__init__.py replaces whatever is missing with a raising stub.
  # Explicit because distro hardening defaults may otherwise inject -z now.
  target_link_options(${target_name} PRIVATE "LINKER:-z,lazy")
endif()

add_custom_command(TARGET ${target_name} POST_BUILD COMMAND ${CMAKE_COMMAND} -E copy "${SWIG_OUTPUT_DIR}/cuvis_il.py"  $<TARGET_FILE_DIR:${target_name}> )

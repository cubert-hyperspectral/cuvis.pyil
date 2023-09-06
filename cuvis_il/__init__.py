import os
import platform
import sys

lib_dir = os.getenv("CUVIS")
if lib_dir is None:
    print('CUVIS environmental variable is not set!')
    sys.exit(1)
if platform.system() == "Windows":
    os.add_dll_directory(lib_dir)
    add_il = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    os.environ['PATH'] += os.pathsep + add_il
    sys.path.append(str(add_il))
elif platform.system() == 'Linux':
    os.environ['PATH'] = lib_dir + os.pathsep + os.environ['PATH']
else:
    raise NotImplementedError('Invalid operating system detected!')
    # sys.exit(1)

del os, platform, sys
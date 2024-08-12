import os
import platform
import sys
import io
import shutil
import glob

from setuptools.command.install import install
from shutil import rmtree, copy
from setuptools import setup, find_packages, Command 
from setuptools.command import develop

here = os.path.abspath(os.path.dirname(__file__))

NAME = 'cuvis_il2'
VERSION = '3.2.1'

NUMPY_VERSION = '1.22.0'

DESCRIPTION = 'Compiled Python Bindings for the CUVIS SDK.'

if (numpy_complied := os.environ.get('CUVIS_NUMPY_COMPILED')) is not None:
    NUMPY_VERSION = numpy_complied

REQUIREMENTS = {
    'install': [
        str(f'numpy >= {NUMPY_VERSION}'),
    ],
}

def get_python_version(sep='.') -> str:
    return f'{sys.version_info.major}{sep}{sys.version_info.minor}'

def get_pyil_files():
    with open(os.path.join(here,f'binary_dir_{platform.python_version()}.stamp')) as f:
        path = f.read().strip('\n')
        if platform.system() == 'Windows':
            files = ['_cuvis_pyil.pyd', 'cuvis_il.py']
            for file in files:
                full_path = os.path.join(path, file)
                copy(full_path, os.path.join(here, 'cuvis_il'))
        elif platform.system() == "Linux" and "Ubuntu" in platform.version():
            files = ['_cuvis_pyil.so', 'cuvis_il.py']
            for file in files:
                full_path = os.path.join(path, file)
                copy(full_path, os.path.join(here, 'cuvis_il'))

lib_dir = ""
if 'CUVIS' in os.environ:
    lib_dir = os.getenv('CUVIS')
    print('CUVIS SDK found at {}!'.format(lib_dir))
else:
    Exception(
        'CUVIS SDK does not seem to exist on this machine! Make sure that the environment variable CUVIS is set.')

# taken from https://github.com/navdeep-G/setup.py/blob/master/setup.py
class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Build and publish the package.'
    user_options = [
         ('username=', None, 'pip Username'),
          ('password=', None, 'pip Password'),
    ]

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        # DEPCRECATED - Use PYPI API for authentication instead
        self.username= '__token__'
        self.password = ''
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            rmtree(os.path.join(here, 'dist'))
            rmtree(os.path.join(here, 'repaired_dist'))
        except OSError:
            pass

        self.status('Copying latest pyil files')
        get_pyil_files()

        # Operating system dependent
        self.status('Building Source and Wheel (universal) distribution…')
        if platform.system() == 'Windows':
            os.system(f'python setup.py bdist_wheel --python-tag=py{get_python_version("")} --plat-name=win_amd64')
            self.status('Uploading the package to PyPI via Twine…')
            os.system(f'twine upload -p {self.password} -u {self.username} -r testpypi dist/*')
        elif platform.system() == "Linux" and "Ubuntu" in platform.version():
            os.system(f'python setup.py bdist_wheel --python-tag=py{get_python_version("")} --plat-name=linux_x86_64')
            # Fix the package to work with manylinux
            whl_file = glob.glob('./dist/*.whl')[0]
            self.status('Repairing build...')
            try:
                os.mkdir('repaired_dist')
            except:
                pass
            #  This creates a build compatible with Ubuntu 20.04
            os.system('auditwheel repair dist/* -w repaired_dist --plat manylinux_2_31_x86_64')
            self.status('Uploading the package to PyPI via Twine…')
            # Make sure .pypirc file is configured
            os.system(f'twine upload -r testpypi repaired_dist/*')
        sys.exit()

class PostInstallCommand(install):
    """Custom install command to move .so file after installation."""

    def run(self):
        # Run the standard install process
        install.run(self)
        # On Windows, no post-install step is necessary
        if platform.system() != "Linux":
            return
        ### .SO FILE
        # Path to the .so file in the source directory
        source_path = os.path.join(os.path.dirname(__file__), '_cuvis_pyil.so')
        # Destination directory (where the .so file should be moved)
        destination_dir = os.path.join(self.install_lib, 'cuvis_il2')
        # Move the .so file
        shutil.copy(source_path, destination_dir)
        ### .PY FILE
        # Path to the .so file in the source directory
        source_path = os.path.join(os.path.dirname(__file__), 'cuvis_il.py')
        # Destination directory (where the .so file should be moved)
        destination_dir = os.path.join(self.install_lib, 'cuvis_il2')
        # Move the .so file
        shutil.copy(source_path, destination_dir)
        print(f"Moved {source_path} to {destination_dir}")

add_il = os.path.join(here, "cuvis_il")

try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION


setup(
    name=NAME,
    python_requires=f'>=3.9',
    version=VERSION,
    packages=find_packages(),
    url='https://www.cubert-hyperspectral.com/',
    license='Apache License 2.0',
    author='Cubert GmbH, Ulm, Germany',
    author_email='SDK@cubert-gmbh.com',
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    #setup_requires=REQUIREMENTS['setup'],
    install_requires=REQUIREMENTS['install'],
    include_package_data=True,
	cmdclass={
        'upload': UploadCommand,
        'install': PostInstallCommand,
    },
)

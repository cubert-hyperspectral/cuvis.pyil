import os
import platform
import sys
import io

from shutil import rmtree, copy
from setuptools import setup, find_packages, Command 
from setuptools.command import develop

here = os.path.abspath(os.path.dirname(__file__))

NAME = 'cuvis_il'
VERSION = '3.2.1b3'

DESCRIPTION = 'Compiled Python Bindings for the CUVIS SDK.'

REQUIREMENTS = {
    'install': [
        str(f'numpy >= 1.22.0'),
    ],
}

def get_python_version(sep='.') -> str:
    return f'{sys.version_info.major}{sep}{sys.version_info.minor}'

def get_pyil_files():
    files = ['_cuvis_pyil.pyd', 'cuvis_il.py']
    with open(os.path.join(here,f'binary_dir_{platform.python_version()}.stamp')) as f:
        path = f.read().strip('\n')

        for file in files:
            full_path = os.path.join(path, file)
            copy(full_path, os.path.join(here, 'cuvis_il'))
    pass

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
        self.username=''
        self.password=''
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        self.status('Copying latest pyil files')
        get_pyil_files()

        self.status('Building Source and Wheel (universal) distribution…')
        os.system(f'python setup.py bdist_wheel --python-tag=py{get_python_version("")} --plat-name=win_amd64')

        self.status('Uploading the package to PyPI via Twine…')
        os.system(f'twine upload -p {self.password} -u {self.username} -r testpypi dist/*')

        #self.status('Pushing git tags…')
        #os.system('git tag v{0}'.format(about['__version__']))
        #os.system('git push --tags')

        sys.exit()

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
    },
)

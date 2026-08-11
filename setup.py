from setuptools import setup, Extension, find_packages
import pybind11
import sys
import os

is_windows = sys.platform == 'win32'
is_linux = sys.platform.startswith('linux')
is_macos = sys.platform == 'darwin'

# Argumentos de compilación y enlace
if is_windows:
    # En Windows, pybind11 ya añade los flags correctos (/EHsc, /MD, etc.)
    # No añadimos nada extra para evitar conflictos
    extra_compile_args = []
    extra_link_args = []
else:
    extra_compile_args = ['-std=c++11', '-O3']
    extra_link_args = ['-shared', '-fPIC'] if is_linux else []

cpp_module = Extension(
    'src.module.cpp_module',
    sources=[
        'cpp_module/detector.cpp',
        'cpp_module/bindings.cpp'
    ],
    include_dirs=[pybind11.get_include()],
    language='c++',
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
)

setup(
    name='compilador_profesional',
    version='1.0.0',
    description='Compilador/Empaquetador con GUI profesional',
    long_description=open('README.md', encoding='utf-8').read() if os.path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    author='Brayan M.',
    author_email='bgarciaguibert@gmail.com',
    url='https://github.com/bryangarcia1204/compiler',
    license='MIT',

    packages=find_packages(),
    ext_modules=[cpp_module],

    install_requires=[
        'PyQt5>=5.15',
        'pybind11>=3.1',
    ],

    entry_points={
        'console_scripts': [
            'compilador = src.main:main',
            'compilador-cli = src.cli:main',
        ]
    },

    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.8',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Compilers',
    ],
)
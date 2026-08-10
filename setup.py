from setuptools import setup, Extension, find_packages
import pybind11
import sys
import os

is_windows = sys.platform == 'win32'
is_linux = sys.platform.startswith('linux')
is_macos = sys.platform == 'darwin'

cpp_module = Extension(
    'src.cpp_module',
    sources=['cpp_module/detector.cpp', 'cpp_module/bindings.cpp'],
    include_dirs=[pybind11.get_include()],
    language='c++',
    extra_compile_args=['-std=c++11', '-O3'],
    extra_link_args=['-shared', '-static', '-static-libgcc', '-static-libstdc++'] if is_windows else
                     ['-shared', '-fPIC'] if (is_linux or is_macos) else []
)

setup(
    name='compilador_profesional',
    version='1.0.0',
    description='Compilador/Empaquetador con GUI profesional',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    ext_modules=[cpp_module],
    install_requires=['PyQt5>=5.15', 'pybind11>=3.1'],
    entry_points={'console_scripts': ['compilador = src.main:main']},
    include_package_data=True,
    python_requires='>=3.8',
)
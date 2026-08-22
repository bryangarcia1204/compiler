from setuptools import setup, Extension
import pybind11
import sys
import os

# Forzar uso de MinGW en Windows
if sys.platform == 'win32':
    # Establecer los compiladores C/C++
    os.environ['CC'] = 'gcc'
    os.environ['CXX'] = 'g++'

cpp_module = Extension(
    'cpp_module',
    sources=[
        'detector.cpp',
        'bindings.cpp'
    ],
    include_dirs=[pybind11.get_include()],
    language='c++',
    extra_compile_args=['-std=c++11'],
    extra_link_args=['-shared', '-static-libgcc', '-static-libstdc++', '-Wl,-Bstatic', '-lwinpthread', '-Wl,-Bdynamic']
)

setup(
    name='cpp_module',
    version='1.0',
    description='Módulo de detección de compiladores en C++',
    ext_modules=[cpp_module],
)
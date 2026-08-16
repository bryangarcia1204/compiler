from setuptools import setup, Extension
import os
import sys
import pybind11

# Directorio actual del script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define el módulo de extensión C++
# Se asume que 'detector_module' será el nombre del módulo importable en Python.
# Los archivos fuente C++ son bindings.cpp y detector.cpp.
# Se incluyen los directorios de pybind11 para que el compilador encuentre los headers.
# Se añaden argumentos de compilación para C++17 (o una versión más moderna).
# Es importante que el compilador C++ utilizado por setuptools soporte esta versión.
# Para Windows, se pueden necesitar argumentos específicos como '/std:c++17'.
# Para Linux/macOS, '-std=c++17' es común.

# Argumentos de compilación específicos del sistema operativo
compile_args = ['-std=c++17']
link_args = []

if sys.platform == "win32":
    compile_args = ['/std:c++17', '/EHsc'] # /EHsc para manejo de excepciones
    # Si libwinpthread-1.dll necesita ser enlazada explícitamente, se añadiría aquí.
    # Sin embargo, a menudo es una dependencia de tiempo de ejecución o se enlaza implícitamente.
    # link_args.append('libwinpthread-1.lib') # Ejemplo, si tuvieras un .lib para ella.
elif sys.platform == "darwin": # macOS
    compile_args = ['-std=c++17', '-stdlib=libc++']
elif sys.platform.startswith("linux"): # Linux
    compile_args = ['-std=c++17']

# Define la extensión
ext_modules = [
    Extension(
        'detector_module',  # Nombre del módulo Python
        sources=[
            os.path.join(current_dir, 'bindings.cpp'),
            os.path.join(current_dir, 'detector.cpp')
        ],
        include_dirs=[
            pybind11.get_include(),
            pybind11.get_include(user=True),
            current_dir # Para detector.h
        ],
        language='c++',
        extra_compile_args=compile_args,
        extra_link_args=link_args,
    ),
]

setup(
    name='cpp_detector',
    version='0.1.0',
    author='Tu Nombre',
    author_email='tu.email@example.com',
    description='Un módulo de extensión C++ para detección de algo.',
    long_description=open('README.md').read() if os.path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    ext_modules=ext_modules,
    # Asegúrate de que pybind11 esté listado como una dependencia de instalación
    # para que se instale si no está presente.
    install_requires=[
        'pybind11>=2.6.0', # Especifica una versión mínima de pybind11
    ],
    # Clasificadores para PyPI
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: C++',
        'License :: OSI Approved :: MIT License', # O la licencia que uses
        'Operating System :: OS Independent',
    ],
    zip_safe=False, # Necesario para módulos de extensión C++
)

# Para construir el módulo, ejecuta:
# python setup.py build_ext --inplace
# O para instalarlo en tu entorno:
# pip install .
# O para crear un wheel:
# python setup.py bdist_wheel
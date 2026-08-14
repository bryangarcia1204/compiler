import os
import sys
import setuptools

# Importar pybind11 para obtener las rutas de inclusión
try:
    import pybind11
except ImportError:
    # Si pybind11 no está instalado, se puede añadir como dependencia de setup_requires
    # o asegurar que esté en el entorno antes de ejecutar setup.py
    print("Error: pybind11 no está instalado. Por favor, instálelo con 'pip install pybind11'.")
    sys.exit(1)

# Directorio actual del script setup.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuración de los argumentos de compilación para C++
# Se usan banderas específicas para MinGW (GCC/Clang)
# -std=c++17: Usar el estándar C++17
# -O3: Nivel de optimización alto
# -Wall -Wextra: Habilitar advertencias
# -g: Incluir información de depuración
# -D_GLIBCXX_USE_CXX11_ABI=0: Puede ser necesario para compatibilidad ABI con algunas versiones de GCC/MinGW
#                              Si se usa una versión reciente de MinGW y pybind11, podría no ser necesario.
#                              Se recomienda probar sin ella primero.
COMPILE_ARGS = [
    '-std=c++17',
    '-O3',
    '-Wall',
    '-Wextra',
    '-g',
    # '-D_GLIBCXX_USE_CXX11_ABI=0' # Descomentar si hay problemas de ABI con la STL
]

# Argumentos de enlace (linker) para C++
# No suelen ser necesarios argumentos adicionales para un módulo simple con pybind11
LINK_ARGS = []

# Definición de la extensión C++
# name: Nombre del módulo Python (cómo se importará)
# sources: Lista de archivos fuente C++
# include_dirs: Directorios donde buscar archivos de cabecera (.h)
#               pybind11.get_include() proporciona la ruta a las cabeceras de pybind11.
# extra_compile_args: Argumentos adicionales para el compilador C++.
# extra_link_args: Argumentos adicionales para el enlazador C++.
cpp_module = setuptools.Extension(
    'cpp_module',
    sources=[
        os.path.join(CURRENT_DIR, 'bindings.cpp'),
        os.path.join(CURRENT_DIR, 'detector.cpp')
    ],
    include_dirs=[
        pybind11.get_include(),
        pybind11.get_include(user=True), # Para cabeceras de usuario de pybind11
        CURRENT_DIR # Para detector.h
    ],
    language='c++',
    extra_compile_args=COMPILE_ARGS,
    extra_link_args=LINK_ARGS,
)

# Configuración de setuptools
setuptools.setup(
    name='compiler_detector',
    version='0.1.0',
    author='Tu Nombre',
    author_email='tu.email@example.com',
    description='Un módulo Python para detectar compiladores usando C++',
    long_description=open('README.md').read() if os.path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    url='https://github.com/tu_usuario/tu_repo',
    packages=setuptools.find_packages(),
    ext_modules=[cpp_module],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Compilers',
    ],
    python_requires='>=3.7',
    install_requires=[
        'pybind11>=2.6.0', # Especifica la versión mínima de pybind11
    ],
    # Si se usa CMake, setup.py podría invocar CMake en lugar de compilar directamente.
    # Para este proyecto, se asume que se puede usar setup.py directamente para compilar.
)

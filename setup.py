from setuptools import setup, Extension, find_packages
import pybind11
import sys
import os

# ============================================================
# DETECCIÓN DE PLATAFORMA
# ============================================================
is_windows = sys.platform == 'win32'
is_linux = sys.platform.startswith('linux')
is_macos = sys.platform == 'darwin'

# ============================================================
# CONFIGURACIÓN DEL MÓDULO C++
# ============================================================

# Forzar compilador en Windows (opcional, pero recomendado)
if is_windows:
    os.environ['CC'] = 'gcc'
    os.environ['CXX'] = 'g++'

# Argumentos de enlace específicos por plataforma
if is_windows:
    extra_link_args = [
        '-shared',
        '-static-libgcc',
        '-static-libstdc++',
        '-Wl,-Bstatic', '-lwinpthread', '-Wl,-Bdynamic'
    ]
elif is_linux:
    extra_link_args = ['-shared', '-fPIC']
else:  # macOS: NO forzar flags, dejar que setuptools añada -bundle
    extra_link_args = []

cpp_module = Extension(
    'src.module.cpp_module',          # Ruta final: src/module/cpp_module.so
    sources=[
        'cpp_module/detector.cpp',
        'cpp_module/bindings.cpp'
    ],
    include_dirs=[pybind11.get_include()],
    language='c++',
    extra_compile_args=['-std=c++11', '-O3'],
    extra_link_args=extra_link_args,
)

# ============================================================
# CONFIGURACIÓN DEL PAQUETE
# ============================================================

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

    # Paquetes: detecta automáticamente src/ y sus submódulos
    packages=find_packages(),

    # Módulo C++
    ext_modules=[cpp_module],

    # Dependencias
    install_requires=[
        'PyQt5>=5.15',
        'pybind11>=3.1',
    ],

    # Puntos de entrada (GUI y CLI)
    entry_points={
        'console_scripts': [
            'compilador = src.main:main',
            'compilador-cli = src.cli:main',
        ]
    },

    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.8',

    # Opciones de compilación (para Windows usa mingw32)
    options={
        'build_ext': {
            'compiler': 'mingw32' if is_windows else 'unix',
        }
    },

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
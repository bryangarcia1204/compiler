from setuptools import setup, Extension, find_packages
import pybind11
import sys
import os

# ============================================================
# CONFIGURACIÓN MULTIPLATAFORMA
# ============================================================
is_windows = sys.platform == 'win32'
is_linux = sys.platform.startswith('linux')
is_macos = sys.platform == 'darwin'

# Forzar compilador en Windows
if is_windows:
    os.environ['CC'] = 'gcc'
    os.environ['CXX'] = 'g++'

# ============================================================
# CONFIGURACIÓN DEL MÓDULO C++
# ============================================================
# Configuración de enlace por plataforma
if is_windows:
    extra_link = [
        '-shared',
        '-static',
        '-static-libgcc',
        '-static-libstdc++',
        '-Wl,-Bstatic', '-lwinpthread', '-Wl,-Bdynamic'
    ]
elif is_linux:
    extra_link = ['-shared', '-fPIC']
else:  # macOS
    # No forzar flags, dejar que setuptools gestione
    extra_link = []

# Definición del módulo
cpp_module = Extension(
    'src.module.cpp_module',
    sources=['cpp_module/detector.cpp', 'cpp_module/bindings.cpp'],
    include_dirs=[pybind11.get_include()],
    language='c++',
    extra_compile_args=['-std=c++11', '-O3'],
    extra_link_args=extra_link,
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
    
    # ⬅️ CAMBIADO: encuentra paquetes en src/
    packages=find_packages(),
    package_dir={'': '.'},
    
    # ⬅️ CAMBIADO: el módulo C++ se instala dentro de src/
    ext_modules=[cpp_module],
    
    install_requires=[
        'PyQt5>=5.15',
        'pybind11>=3.1',
    ],
    
    entry_points={
        'console_scripts': [
            'compilador = src.main:main',  # ⬅️ CAMBIADO: punto de entrada
            'compilador-cli = src.cli:main',
        ]
    },
    
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.8',
    
    # ⬅️ CAMBIADO: opciones de compilación
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
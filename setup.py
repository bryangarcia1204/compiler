from setuptools import setup, Extension, find_packages
import pybind11
import sys
import os

# ---------- CONFIGURACIÓN PARA USAR MINGW ----------

# Configuración del módulo C++
is_windows = sys.platform == 'win32'

if is_windows:
    # Establecer los compiladores C/C++
    os.environ['CC'] = 'gcc'
    os.environ['CXX'] = 'g++'

cpp_module = Extension(
    'cpp_module',
    sources=[
        'cpp_module/detector.cpp',
        'cpp_module/bindings.cpp'
    ],
    include_dirs=[pybind11.get_include()],
    language='c++',
    extra_compile_args=['-std=c++11'],
    extra_link_args=(
        [
            '-shared',
            '-static-libgcc',
            '-static-libstdc++',
            '-Wl,-Bstatic',
            '-lwinpthread',
            '-Wl,-Bdynamic'
        ] if is_windows else []
    )
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
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    ext_modules=[cpp_module],
    install_requires=[
        'PyQt5>=5.15',
        'pybind11>=3.1',
    ],
    entry_points={
        'console_scripts': [
            'compilador = main:main',
        ]
    },
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.8',
    options={
        'build_ext': {
            'compiler': 'mingw32' if is_windows else 'unix' or 'clang',
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
    ],
)
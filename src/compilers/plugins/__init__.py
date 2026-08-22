# src/compilers/plugins/__init__.py
"""
Plugins de la comunidad para el Compilador Profesional.
Los archivos .py en este directorio se cargan automáticamente.
"""

from .clang import ClangStrategy
from .emcc import EmscriptenStrategy
from .pkg import PkgStrategy
from .pyinstaller import PyInstallerStrategy
from .python_build import PythonBuildStrategy

STRATEGY_CLASSES = [
    PyInstallerStrategy,
    PkgStrategy,
    PythonBuildStrategy,
    EmscriptenStrategy,
    ClangStrategy,
]

for cls in STRATEGY_CLASSES:
    globals()[cls.__name__] = cls

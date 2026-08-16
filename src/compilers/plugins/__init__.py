# src/compilers/plugins/__init__.py
"""
Plugins de la comunidad para el Compilador Profesional.
Los archivos .py en este directorio se cargan automáticamente.
"""
from ..built_in.dotnet import DotnetStrategy
from .pyinstaller import PyInstallerStrategy
from .pkg import PkgStrategy
from .python_build import PythonBuildStrategy
from .emcc import EmscriptenStrategy
from .clang import ClangStrategy

STRATEGY_CLASSES = [
    DotnetStrategy,
    PyInstallerStrategy,
    PkgStrategy,
    PythonBuildStrategy,
    EmscriptenStrategy,
    ClangStrategy
]

for cls in STRATEGY_CLASSES:
    globals()[cls.__name__] = cls
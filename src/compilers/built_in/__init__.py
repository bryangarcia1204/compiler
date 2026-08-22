# src/compilers/builtin/__init__.py
from .dotnet import DotnetStrategy
from .gcc import GCCStrategy
from .go import GoStrategy
from .gpp import GPPStrategy
from .java import JavaStrategy
from .node import NodeStrategy
from .python import PythonStrategy
from .rust import RustStrategy

STRATEGY_CLASSES = [
    GCCStrategy,
    GPPStrategy,
    RustStrategy,
    GoStrategy,
    JavaStrategy,
    PythonStrategy,
    NodeStrategy,
    DotnetStrategy,
]

# Registrar cada clase con su STRATEGY_CLASS
for cls in STRATEGY_CLASSES:
    globals()[cls.__name__] = cls

# src/compilers/builtin/__init__.py
from .gcc import GCCStrategy
from .gpp import GPPStrategy
from .rust import RustStrategy
from .go import GoStrategy
from .java import JavaStrategy
from .python import PythonStrategy
from .node import NodeStrategy

STRATEGY_CLASSES = [
    GCCStrategy,
    GPPStrategy,
    RustStrategy,
    GoStrategy,
    JavaStrategy,
    PythonStrategy,
    NodeStrategy
]

# Registrar cada clase con su STRATEGY_CLASS
for cls in STRATEGY_CLASSES:
    globals()[cls.__name__] = cls
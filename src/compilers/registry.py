import importlib
import pkgutil
from typing import Dict, Optional, Type

from .base import CompilerStrategy

class CompilerRegistry:
    _strategies: Dict[str, Type[CompilerStrategy]] = {}
    _loaded = False

    @classmethod
    def register(cls, strategy_class: Type[CompilerStrategy]) -> None:
        instance = strategy_class()
        cls._strategies[instance.tool_name.lower()] = strategy_class

    @classmethod
    def get(cls, tool_name: str) -> Optional[CompilerStrategy]:
        cls._load_all()
        strategy_class = cls._strategies.get(tool_name.lower())
        if strategy_class:
            return strategy_class()
        return None

    @classmethod
    def get_all(cls) -> Dict[str, Type[CompilerStrategy]]:
        cls._load_all()
        return cls._strategies

    @classmethod
    def _load_all(cls) -> None:
        if cls._loaded:
            return

        # Cargar builtins
        try:
            from . import built_in
            for module_info in pkgutil.iter_modules(built_in.__path__, prefix='src.compilers.builtin.'):
                module = importlib.import_module(module_info.name)
                if hasattr(module, 'STRATEGY_CLASS'):
                    cls.register(module.STRATEGY_CLASS)
        except ImportError:
            pass

        # Cargar plugins
        try:
            from . import plugins
            for module_info in pkgutil.iter_modules(plugins.__path__, prefix='src.compilers.plugins.'):
                module = importlib.import_module(module_info.name)
                if hasattr(module, 'STRATEGY_CLASS'):
                    cls.register(module.STRATEGY_CLASS)
        except ImportError:
            pass

        cls._loaded = True
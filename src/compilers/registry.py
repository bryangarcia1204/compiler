import importlib
import pkgutil
from typing import Dict, Optional, Type

from .base import CompilerStrategy

class CompilerRegistry:
    """
    Registro central de estrategias de compilación.
    """

    _strategies: Dict[str, Type[CompilerStrategy]] = {}
    _loaded = False

    @classmethod
    def register(cls, strategy_class: Type[CompilerStrategy]) -> None:
        """Registra una estrategia."""
        instance = strategy_class()
        cls._strategies[instance.tool_name.lower()] = strategy_class

    @classmethod
    def get(cls, tool_name: str) -> Optional[CompilerStrategy]:
        """Obtiene una instancia de la estrategia para la herramienta."""
        cls._load_all()
        strategy_class = cls._strategies.get(tool_name.lower())
        if strategy_class:
            return strategy_class()
        return None
    
    @classmethod
    def get_all(cls) -> Dict[str, type[CompilerStrategy]]:
        cls._load_all()
        strategy_class = cls._strategies
        return strategy_class

    @classmethod
    def _load_all(cls) -> None:
        """Carga estrategias integradas y plugins de la comunidad."""
        if cls._loaded:
            return

        # Cargar estrategias integradas (builtin)
        try:
            from . import built_in
            for module_info in pkgutil.iter_modules(built_in.__path__, prefix='src.compilers.builtin.'):
                module = importlib.import_module(module_info.name)
                if hasattr(module, 'STRATEGY_CLASS'):
                    cls.register(module.STRATEGY_CLASS)
        except ImportError:
            pass

        # Cargar plugins (NUEVO)
        try:
            from . import plugins
            for module_info in pkgutil.iter_modules(plugins.__path__, prefix='src.compilers.plugins.'):
                module = importlib.import_module(module_info.name)
                if hasattr(module, 'STRATEGY_CLASS'):
                    cls.register(module.STRATEGY_CLASS)
        except ImportError:
            pass

        cls._loaded = True
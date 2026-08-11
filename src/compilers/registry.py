import importlib
import pkgutil
import os
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
    def _load_all(cls) -> None:
        """Carga estrategias integradas y plugins de la comunidad."""
        if cls._loaded:
            return

        # Cargar estrategias integradas (builtin)
        try:
            from . import builtin
            for module_info in pkgutil.iter_modules(builtin.__path__, prefix='src.compilers.builtin.'):
                module = importlib.import_module(module_info.name)
                if hasattr(module, 'STRATEGY_CLASS'):
                    cls.register(module.STRATEGY_CLASS)
        except ImportError:
            pass

        # Cargar plugins de la comunidad (directorio plugins/)
        plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
        if os.path.exists(plugins_dir):
            for module_info in pkgutil.iter_modules([plugins_dir]):
                module = importlib.import_module(f'.plugins.{module_info.name}', package='src.compilers')
                if hasattr(module, 'STRATEGY_CLASS'):
                    cls.register(module.STRATEGY_CLASS)

        cls._loaded = True
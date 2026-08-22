# src/plugins_market/plugin_loader.py
"""
Cargador dinámico de plugins.
Permite cargar plugins desde archivos, directorios o el registro.
Integración completa con PluginManager y PluginRegistry.
"""

import importlib
import importlib.util
import inspect
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Type

from ..compilers.base import CompilerStrategy
from ..compilers.registry import CompilerRegistry
from ..utils import logger
from .plugin_registry import PluginRegistry, PluginStatus

log = logger.Logger()


class PluginLoader:
    """Cargador dinámico de plugins con integración completa."""

    PLUGINS_DIR = Path(__file__).parent.parent / "compilers" / "plugins"
    _loaded_plugins: Dict[str, Type[CompilerStrategy]] = {}
    _callbacks: List[Callable] = []

    @classmethod
    def load_from_file(cls, filepath: Path) -> Optional[Type[CompilerStrategy]]:
        """
        Carga un plugin desde un archivo Python.

        Args:
            filepath: Ruta al archivo del plugin

        Returns:
            La clase STRATEGY_CLASS si se encuentra, None en caso contrario.
        """
        if not filepath.exists():
            log.error(f"[PluginLoader] Archivo no existe: {filepath}")
            return None

        try:
            # Importar el módulo usando importlib con el contexto del paquete
            # Esto permite que los imports relativos funcionen
            module_name = f"src.compilers.plugins.{filepath.stem}"

            # Si el módulo ya está cargado, recargarlo
            if module_name in sys.modules:
                module = sys.modules[module_name]
                importlib.reload(module)
            else:
                # Crear un loader que maneje correctamente los imports relativos
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                if spec is None or spec.loader is None:
                    log.error(f"[PluginLoader] No se pudo cargar el archivo: {filepath}")
                    return None

                module = importlib.util.module_from_spec(spec)
                # Añadir el módulo al sys.modules ANTES de ejecutarlo
                # para que los imports relativos funcionen
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            # Buscar STRATEGY_CLASS
            if hasattr(module, "STRATEGY_CLASS"):
                strategy_class = getattr(module, "STRATEGY_CLASS")
                if inspect.isclass(strategy_class) and issubclass(strategy_class, CompilerStrategy):
                    log.debug(f"[PluginLoader] Plugin cargado: {strategy_class.__name__}")
                    return strategy_class
                else:
                    log.error(
                        "[PluginLoader] STRATEGY_CLASS no es una subclase de CompilerStrategy"
                    )
            else:
                log.warning(f"[PluginLoader] No se encontró STRATEGY_CLASS en {filepath.name}")

        except Exception as e:
            log.error(f"[PluginLoader] Error cargando plugin {filepath.name}: {e}")

        return None

    @classmethod
    def load_from_directory(cls, directory: Path) -> List[Type[CompilerStrategy]]:
        """
        Carga todos los plugins de un directorio.

        Returns:
            Lista de clases de estrategia cargadas.
        """
        loaded = []
        if not directory.exists():
            log.warning(f"[PluginLoader] Directorio no existe: {directory}")
            return loaded

        for file in directory.glob("*.py"):
            if file.name.startswith("__"):
                continue
            strategy = cls.load_from_file(file)
            if strategy:
                loaded.append(strategy)
                # Guardar referencia
                cls._loaded_plugins[file.stem] = strategy

        return loaded

    @classmethod
    def load_all_plugins(cls, registry: Optional[PluginRegistry] = None) -> int:
        """
        Carga todos los plugins del directorio de plugins.
        Actualiza el estado en PluginRegistry si se proporciona.

        Args:
            registry: Instancia de PluginRegistry para actualizar estados

        Returns:
            Número de plugins cargados.
        """
        loaded = 0
        cls._loaded_plugins.clear()

        # Primero, intentar importar plugins que ya están en el paquete
        # (los que no están en el directorio de plugins)
        try:
            import pkgutil

            import src.compilers.plugins as plugins_package

            for module_info in pkgutil.iter_modules(
                plugins_package.__path__, prefix="src.compilers.plugins."
            ):
                try:
                    module = importlib.import_module(module_info.name)
                    if hasattr(module, "STRATEGY_CLASS"):
                        strategy_class = getattr(module, "STRATEGY_CLASS")
                        if inspect.isclass(strategy_class) and issubclass(
                            strategy_class, CompilerStrategy
                        ):
                            CompilerRegistry.register(strategy_class)
                            plugin_id = module_info.name.split(".")[-1]
                            cls._loaded_plugins[plugin_id] = strategy_class
                            loaded += 1
                            log.debug(f"[PluginLoader] Plugin {plugin_id} cargado desde paquete")
                except Exception as e:
                    log.error(f"[PluginLoader] Error cargando plugin del paquete: {e}")
        except ImportError as e:
            log.error(f"Error importando plagins: {e}")

        # Luego, cargar plugins del directorio
        for file in cls.PLUGINS_DIR.glob("*.py"):
            if file.name.startswith("__"):
                continue

            plugin_id = file.stem
            strategy_class = cls.load_from_file(file)

            if strategy_class:
                try:
                    CompilerRegistry.register(strategy_class)
                    cls._loaded_plugins[plugin_id] = strategy_class
                    loaded += 1

                    # Actualizar estado en registry si se proporciona
                    if registry:
                        plugin = registry.get_plugin(plugin_id)
                        if plugin:
                            plugin.status = PluginStatus.ACTIVE
                            plugin.active = True
                            registry.update_plugin(plugin_id, plugin)
                        else:
                            # Si no está registrado, crearlo con estado activo
                            from .plugin_registry import PluginMetadata

                            metadata = PluginMetadata(
                                id=plugin_id,
                                name=file.stem.replace("_", " ").title(),
                                version="0.0.1",
                                description=f"Plugin {file.stem} cargado automáticamente",
                                author="Unknown",
                                installed_at=datetime.now().isoformat(),
                                active=True,
                                status=PluginStatus.ACTIVE,
                                strategy_class=strategy_class.__name__,
                            )
                            registry.add_plugin(metadata)

                    log.debug(f"[PluginLoader] Plugin {plugin_id} cargado y registrado")

                except Exception as e:
                    log.error(f"[PluginLoader] Error registrando plugin {plugin_id}: {e}")

        log.debug(f"[PluginLoader] Cargados {loaded} plugins")
        cls._notify_callbacks()
        return loaded

    @classmethod
    def load_plugin_by_id(cls, plugin_id: str, registry: Optional[PluginRegistry] = None) -> bool:
        """
        Carga un plugin específico por su ID.

        Args:
            plugin_id: ID del plugin (nombre del archivo sin extensión)
            registry: PluginRegistry para actualizar estado

        Returns:
            True si se cargó correctamente, False en caso contrario.
        """
        # Primero, intentar importar como módulo del paquete
        try:
            module = importlib.import_module(f"src.compilers.plugins.{plugin_id}")
            if hasattr(module, "STRATEGY_CLASS"):
                strategy_class = getattr(module, "STRATEGY_CLASS")
                if inspect.isclass(strategy_class) and issubclass(strategy_class, CompilerStrategy):
                    CompilerRegistry.register(strategy_class)
                    cls._loaded_plugins[plugin_id] = strategy_class
                    if registry:
                        plugin = registry.get_plugin(plugin_id)
                        if plugin:
                            plugin.status = PluginStatus.ACTIVE
                            plugin.active = True
                            registry.update_plugin(plugin_id, plugin)
                    log.info(f"[PluginLoader] Plugin {plugin_id} cargado desde paquete")
                    cls._notify_callbacks()
                    return True
        except ImportError:
            pass

        # Si no está en el paquete, cargar desde archivo
        filepath = cls.PLUGINS_DIR / f"{plugin_id}.py"
        strategy_class = cls.load_from_file(filepath)

        if strategy_class:
            try:
                CompilerRegistry.register(strategy_class)
                cls._loaded_plugins[plugin_id] = strategy_class

                if registry:
                    plugin = registry.get_plugin(plugin_id)
                    if plugin:
                        plugin.status = PluginStatus.ACTIVE
                        plugin.active = True
                        registry.update_plugin(plugin_id, plugin)

                log.info(f"[PluginLoader] Plugin {plugin_id} cargado y registrado")
                cls._notify_callbacks()
                return True

            except Exception as e:
                log.error(f"[PluginLoader] Error registrando {plugin_id}: {e}")
                return False

        return False

    @classmethod
    def unload_plugin(cls, plugin_id: str) -> bool:
        """
        Descarga un plugin (elimina del registro).

        Nota: Esto no elimina el archivo, solo lo desactiva.
        """
        if plugin_id in cls._loaded_plugins:
            del cls._loaded_plugins[plugin_id]
            log.info(f"[PluginLoader] Plugin {plugin_id} descargado")
            cls._notify_callbacks()
            return True
        return False

    @classmethod
    def reload_plugin(cls, plugin_id: str, registry: Optional[PluginRegistry] = None) -> bool:
        """
        Recarga un plugin (útil para desarrollo).

        Args:
            plugin_id: ID del plugin
            registry: PluginRegistry para actualizar estado

        Returns:
            True si se recargó correctamente.
        """
        # Eliminar del caché de módulos para forzar recarga
        module_name = f"src.compilers.plugins.{plugin_id}"
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Descargar primero
        cls.unload_plugin(plugin_id)
        # Luego cargar de nuevo
        return cls.load_plugin_by_id(plugin_id, registry)

    @classmethod
    def get_loaded_plugins(cls) -> Dict[str, Type[CompilerStrategy]]:
        """Obtiene los plugins cargados actualmente."""
        return cls._loaded_plugins.copy()

    @classmethod
    def get_loaded_ids(cls) -> List[str]:
        """Obtiene los IDs de los plugins cargados."""
        return list(cls._loaded_plugins.keys())

    @classmethod
    def is_loaded(cls, plugin_id: str) -> bool:
        """Verifica si un plugin está cargado."""
        return plugin_id in cls._loaded_plugins

    @classmethod
    def register_callback(cls, callback: Callable):
        """Registra un callback que se ejecuta cuando cambia el estado de los plugins."""
        cls._callbacks.append(callback)

    @classmethod
    def _notify_callbacks(cls):
        """Notifica a los callbacks registrados."""
        for callback in cls._callbacks:
            try:
                callback(cls._loaded_plugins)
            except Exception as e:
                log.error(f"[PluginLoader] Error en callback: {e}")

    @classmethod
    def create_plugin_template(cls, name: str, languages: List[str]) -> str:
        """
        Genera una plantilla para un nuevo plugin.

        Args:
            name: Nombre del plugin
            languages: Lenguajes soportados

        Returns:
            Código de la plantilla del plugin.
        """
        ext_str = ", ".join(f"'.{lang}'" for lang in languages)

        return f'''# {name}.py
"""
Plugin: {name}
Generado por Compilador Profesional
"""

from typing import List, Tuple, Optional, Any
from src.compilers.base import CompilerStrategy


class {name.capitalize()}Strategy(CompilerStrategy):
    """
    Estrategia para {name}.
    """

    @property
    def tool_name(self) -> str:
        return '{name}'

    @property
    def supported_extensions(self) -> List[str]:
        return [{ext_str}]

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        """
        Construye el comando de compilación para {name}.
        """
        extra_args = extra_args or []
        cmd = ['{name}', file_path]

        if output_path:
            cmd.extend(['-o', output_path])

        if release_mode:
            cmd.append('--release')

        if extra_args:
            cmd.extend(extra_args)

        return cmd, None, []

    def generate_config_files(self, project_info: dict, target: str = 'native') -> dict:
        """
        Genera archivos de configuración para {name}.
        """
        return {{
            '.{name}-config': '# Configuración para {name}\\n# Generado automáticamente'
        }}


STRATEGY_CLASS = {name.capitalize()}Strategy
'''

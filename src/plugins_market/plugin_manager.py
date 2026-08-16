# src/plugins_market/plugin_manager.py
"""
Gestor de plugins: instalación, desinstalación, actualización.
"""

import os
import shutil
import subprocess
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Type
from datetime import datetime

from .plugin_registry import PluginRegistry, PluginMetadata, PluginStatus
from .plugin_loader import PluginLoader
from .market_client import MarketClient
from .. import logger

log = logger.Logger()


class PluginManager:
    """Gestiona la instalación, desinstalación y carga de plugins."""

    PLUGINS_DIR = Path(__file__).parent.parent / "compilers" / "plugins"

    def __init__(self):
        self.registry = PluginRegistry()
        self.market = MarketClient()

    def install_plugin(self, plugin_id: str, version: Optional[str] = None) -> bool:
        """
        Instala un plugin desde el marketplace.
        """
        # Verificar si ya está instalado
        if self.registry.is_installed(plugin_id):
            log.warning(f"[PluginManager] Plugin {plugin_id} ya está instalado.")
            return False

        # Obtener información del marketplace
        plugin_info = self.market.get_plugin_info(plugin_id, version)
        if not plugin_info:
            log.error(f"[PluginManager] Plugin {plugin_id} no encontrado en el marketplace.")
            return False

        # Verificar dependencias
        deps = plugin_info.get('dependencies', [])
        for dep in deps:
            if not self.registry.is_installed(dep):
                # Intentar instalar dependencia automáticamente
                if not self.install_plugin(dep):
                    log.error(f"[PluginManager] Dependencia {dep} no se pudo instalar.")
                    return False

        # Descargar el plugin
        plugin_content = self.market.download_plugin(plugin_id, version)
        if not plugin_content:
            log.error(f"[PluginManager] No se pudo descargar el plugin {plugin_id}.")
            return False

        # Guardar el archivo del plugin
        plugin_file = self.PLUGINS_DIR / f"{plugin_id}.py"
        try:
            self.PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
            with open(plugin_file, 'w', encoding='utf-8') as f:
                f.write(plugin_content)
        except Exception as e:
            log.error(f"[PluginManager] Error guardando plugin {plugin_id}: {e}")
            return False

        # Registrar el plugin
        metadata = PluginMetadata(
            id=plugin_id,
            name=plugin_info.get('name', plugin_id),
            version=plugin_info.get('version', '0.0.1'),
            description=plugin_info.get('description', ''),
            author=plugin_info.get('author', 'Unknown'),
            email=plugin_info.get('email'),
            homepage=plugin_info.get('homepage'),
            repository=plugin_info.get('repository'),
            dependencies=plugin_info.get('dependencies', []),
            supported_languages=plugin_info.get('supported_languages', []),
            supported_platforms=plugin_info.get('supported_platforms', []),
            min_compiler_version=plugin_info.get('min_compiler_version', '1.0.0'),
            max_compiler_version=plugin_info.get('max_compiler_version'),
            installed_at=datetime.now().isoformat(),
            active=True,
            status=PluginStatus.INSTALLED,
            strategy_class=plugin_info.get('strategy_class'),
        )

        self.registry.add_plugin(metadata)
        log.info(f"[PluginManager] Plugin {plugin_id} instalado correctamente.")

        if self.load_plugin(plugin_id):
            log.info(f"[PluginManager] Plugin {plugin_id} instalado y cargado.")
        else:
            log.warning(f"[PluginManager] Plugin {plugin_id} instalado pero no se pudo cargar.")

        return True

    def uninstall_plugin(self, plugin_id: str) -> bool:
        """Desinstala un plugin."""
        if not self.registry.is_installed(plugin_id):
            log.warning(f"[PluginManager] Plugin {plugin_id} no está instalado.")
            return False

        # Verificar si hay plugins que dependen de este
        for p in self.registry.get_installed_plugins():
            if plugin_id in p.dependencies:
                log.warning(f"[PluginManager] No se puede desinstalar {plugin_id}, depende de {p.name}.")
                return False

        # Eliminar el archivo
        plugin_file = self.PLUGINS_DIR / f"{plugin_id}.py"
        try:
            if plugin_file.exists():
                plugin_file.unlink()
        except Exception as e:
            log.error(f"[PluginManager] Error eliminando plugin {plugin_id}: {e}")

        # Eliminar del registro
        self.registry.remove_plugin(plugin_id)
        log.info(f"[PluginManager] Plugin {plugin_id} desinstalado.")
        return True

    def update_plugin(self, plugin_id: str) -> bool:
        """Actualiza un plugin a la última versión."""
        if not self.registry.is_installed(plugin_id):
            log.warning(f"[PluginManager] Plugin {plugin_id} no está instalado.")
            return False

        current = self.registry.get_plugin(plugin_id)
        latest = self.market.get_latest_version(plugin_id)

        if not latest or latest == current.version:
            log.info(f"[PluginManager] Plugin {plugin_id} ya está actualizado.")
            return True

        # Desinstalar versión anterior
        if not self.uninstall_plugin(plugin_id):
            return False

        # Instalar nueva versión
        return self.install_plugin(plugin_id, latest)

    def activate_plugin(self, plugin_id: str) -> bool:
        """Activa un plugin instalado."""
        if not self.registry.is_installed(plugin_id):
            return False

        # Cargar el plugin para verificar que funciona
        if not self.load_plugin(plugin_id):
            return False

        return self.registry.set_active(plugin_id, True)

    def deactivate_plugin(self, plugin_id: str) -> bool:
        """Desactiva un plugin."""
        if not self.registry.is_installed(plugin_id):
            return False
        return self.registry.set_active(plugin_id, False)

    def load_all_plugins(self) -> int:
        """Carga todos los plugins activos usando PluginLoader."""
        return PluginLoader.load_all_plugins(self.registry)

    def load_plugin(self, plugin_id: str) -> bool:
        """Carga un plugin usando PluginLoader."""
        return PluginLoader.load_plugin_by_id(plugin_id, self.registry)

    def unload_plugin(self, plugin_id: str) -> bool:
        """Descarga un plugin usando PluginLoader."""
        return PluginLoader.unload_plugin(plugin_id)

    def reload_plugin(self, plugin_id: str) -> bool:
        """Recarga un plugin usando PluginLoader."""
        return PluginLoader.reload_plugin(plugin_id, self.registry)

    from ..compilers import CompilerStrategy
    def get_loaded_plugins(self) -> Dict[str, Type[CompilerStrategy]]:
        """Obtiene los plugins cargados actualmente."""
        return PluginLoader.get_loaded_plugins()

    def is_loaded(self, plugin_id: str) -> bool:
        """Verifica si un plugin está cargado."""
        return PluginLoader.is_loaded(plugin_id)

    def get_available_plugins(self) -> List[Dict]:
        """Obtiene la lista de plugins disponibles en el marketplace."""
        return self.market.list_plugins()

    def get_installed_plugins(self) -> List[PluginMetadata]:
        """Obtiene la lista de plugins instalados."""
        return self.registry.get_installed_plugins()
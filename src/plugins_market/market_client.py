# src/plugins_market/market_client.py
"""
Cliente para comunicarse con el marketplace de plugins.
"""

import json
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Any
from .. import logger

log = logger.Logger()


class MarketClient:
    """Cliente del marketplace de plugins."""

    # URL del repositorio oficial (puede ser local o remoto)
    DEFAULT_REPO_URL = "https://raw.githubusercontent.com/bryangarcia1204/compiler-plugins/main/data/plugins_registry.json"
    LOCAL_REPO_FILE = "plugins_repo.json"

    def __init__(self, repo_url: Optional[str] = None):
        self.repo_url = repo_url or self.DEFAULT_REPO_URL
        self._cache = None

    def _load_repo(self) -> Dict:
        """Carga el repositorio de plugins."""
        if self._cache is not None:
            return self._cache

        # Intentar desde URL
        try:
            with urllib.request.urlopen(self.repo_url, timeout=5) as response:
                data = response.read().decode('utf-8')
                self._cache = json.loads(data)
                return self._cache
        except Exception as e:
            log.debug(f"[MarketClient] No se pudo cargar desde URL: {e}")

        # Fallback: intentar archivo local
        try:
            with open(self.LOCAL_REPO_FILE, 'r', encoding='utf-8') as f:
                self._cache = json.load(f)
                return self._cache
        except Exception as e:
            log.debug(f"[MarketClient] No se pudo cargar archivo local: {e}")

        self._cache = {"plugins": []}
        return self._cache

    def list_plugins(self) -> List[Dict]:
        """Lista todos los plugins disponibles."""
        repo = self._load_repo()
        return repo.get('plugins', [])

    def get_plugin_info(self, plugin_id: str, version: Optional[str] = None) -> Optional[Dict]:
        """Obtiene información de un plugin específico."""
        plugins = self.list_plugins()
        for plugin in plugins:
            if plugin.get('id') == plugin_id:
                if version:
                    # Buscar versión específica
                    for v in plugin.get('versions', []):
                        if v.get('version') == version:
                            return {**plugin, **v}
                # Si no se pide versión, devolver la última
                versions = plugin.get('versions', [])
                if versions:
                    return {**plugin, **versions[-1]}
                return plugin
        return None

    def get_latest_version(self, plugin_id: str) -> Optional[str]:
        """Obtiene la última versión de un plugin."""
        info = self.get_plugin_info(plugin_id)
        if info:
            return info.get('version')
        return None

    def download_plugin(self, plugin_id: str, version: Optional[str] = None) -> Optional[str]:
        """Descarga el código fuente de un plugin."""
        info = self.get_plugin_info(plugin_id, version)
        if not info:
            return None

        # Intentar descargar desde la URL del plugin
        download_url = info.get('download_url')
        if download_url:
            try:
                with urllib.request.urlopen(download_url, timeout=10) as response:
                    return response.read().decode('utf-8')
            except Exception as e:
                log.error(f"[MarketClient] Error descargando {plugin_id}: {e}")

        # Fallback: usar el contenido embebido
        return info.get('content')

    def refresh(self) -> None:
        """Fuerza la recarga del repositorio."""
        self._cache = None
        self._load_repo()
"""Pruebas para el gestor de configuración."""

import os
import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.config_manager import (
    load_config, save_config, load_project_state,
    save_project_state, clear_project_state, CONFIG_DIR
)


class TestConfigManager:
    """Pruebas para el gestor de configuración."""

    def setup_method(self):
        """Configuración antes de cada prueba."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_dir = CONFIG_DIR

        # Parchear CONFIG_DIR
        import src.config_manager
        src.config_manager.CONFIG_DIR = Path(self.temp_dir)
        src.config_manager.CONFIG_PATH = src.config_manager.CONFIG_DIR / 'config.json'
        src.config_manager.PROJECT_STATE_PATH = src.config_manager.CONFIG_DIR / 'project_state.json'

    def teardown_method(self):
        """Limpieza después de cada prueba."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_config_empty(self):
        """Prueba cargar configuración cuando no existe."""
        config = load_config()
        assert config == {}

    def test_save_and_load_config(self):
        """Prueba guardar y cargar configuración."""
        data = {'last_file': 'test.py', 'release_mode': True}
        save_config(data)

        loaded = load_config()
        assert loaded['last_file'] == 'test.py'
        assert loaded['release_mode'] is True

    def test_save_and_load_project_state(self):
        """Prueba guardar y cargar estado del proyecto."""
        state = {
            'project_dir': '/tmp/project',
            'summary': {'project_type': 'extension'},
            'generated_files': {'Makefile': 'content'},
            'last_modified': '2024-01-01T00:00:00'
        }
        save_project_state(state)

        loaded = load_project_state()
        assert loaded['project_dir'] == '/tmp/project'
        assert loaded['summary']['project_type'] == 'extension'
        assert 'generated_files' in loaded
        assert 'last_modified' in loaded

    def test_clear_project_state(self):
        """Prueba limpiar el estado del proyecto."""
        state = {'project_dir': '/tmp/test'}
        save_project_state(state)
        assert load_project_state() is not None

        clear_project_state()
        loaded = load_project_state()
        assert loaded is None

    def test_config_dir_created(self):
        """Prueba que el directorio de configuración se crea automáticamente."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        save_config({'test': 'value'})
        assert os.path.exists(self.temp_dir)
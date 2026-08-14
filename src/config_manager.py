# src/config_manager.py
"""
Gestión de configuración y persistencia del estado del proyecto.
"""

import json
import os
import platform
from pathlib import Path
from typing import Dict, Optional, Any

# Configuración multiplataforma
if platform.system() == 'Windows':
    CONFIG_DIR = Path(os.environ.get('APPDATA', '')) / 'compilador'
else:
    CONFIG_DIR = Path.home() / '.config' / 'compilador'

CONFIG_PATH = CONFIG_DIR / 'config.json'
PROJECT_STATE_PATH = CONFIG_DIR / 'project_state.json'


def load_config() -> Dict:
    """Carga la configuración general."""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_config(data: Dict) -> None:
    """Guarda la configuración general."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_project_state() -> Optional[Dict]:
    """Carga el estado guardado del proyecto."""
    try:
        if PROJECT_STATE_PATH.exists():
            with open(PROJECT_STATE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def save_project_state(state: Dict) -> None:
    """
    Guarda el estado del proyecto.

    Args:
        state: Diccionario con:
            - project_dir: str
            - summary: dict (el análisis completo)
            - generated_files: dict
            - edited_files: dict
            - build_command: dict
            - last_modified: str (timestamp)
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Añadir timestamp
        from datetime import datetime
        state['last_modified'] = datetime.now().isoformat()
        with open(PROJECT_STATE_PATH, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def clear_project_state() -> None:
    """Elimina el estado guardado del proyecto."""
    try:
        if PROJECT_STATE_PATH.exists():
            PROJECT_STATE_PATH.unlink()
    except Exception:
        pass
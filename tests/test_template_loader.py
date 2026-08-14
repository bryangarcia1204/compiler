"""Pruebas para el cargador de plantillas."""

import os
import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.proyect_editor.template_loader import TemplateLoader


@pytest.fixture
def temp_templates_db():
    """Crea un archivo temporal de base de datos de plantillas."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        db = {
            "version": "1.0.0",
            "languages": {
                "python": {
                    "display_name": "Python",
                    "extensions": [".py", ".pyw"],
                    "config_files": {
                        "requirements.txt": {
                            "description": "Dependencias",
                            "template": "# Dependencias\nnumpy>=1.0.0"
                        },
                        "setup.py": {
                            "description": "Setup",
                            "template": "from setuptools import setup\nsetup(name='{project_name}')"
                        }
                    },
                    "build_commands": {
                        "build": "python -m build"
                    }
                },
                "cpp": {
                    "display_name": "C++",
                    "extensions": [".cpp", ".hpp"],
                    "config_files": {
                        "Makefile": {
                            "description": "Makefile",
                            "template": "CXX = g++\nTARGET = {project_name}"
                        }
                    },
                    "build_commands": {
                        "build": "make"
                    }
                }
            }
        }
        json.dump(db, f)
        f.flush()
        yield f.name


class TestTemplateLoader:
    """Pruebas para TemplateLoader."""

    def test_load_templates(self, temp_templates_db):
        """Prueba la carga de plantillas."""
        loader = TemplateLoader(templates_path=temp_templates_db)
        assert 'languages' in loader.db
        assert 'python' in loader.db['languages']
        assert 'cpp' in loader.db['languages']

    def test_get_language_info(self, temp_templates_db):
        """Prueba obtener información de un lenguaje."""
        loader = TemplateLoader(templates_path=temp_templates_db)
        info = loader.get_language_info('python')
        assert info['display_name'] == 'Python'
        assert '.py' in info['extensions']

    def test_get_template(self, temp_templates_db):
        """Prueba obtener una plantilla específica."""
        loader = TemplateLoader(templates_path=temp_templates_db)
        template = loader.get_template('python', 'requirements.txt')
        assert 'numpy>=1.0.0' in template

    def test_get_all_templates_for_language(self, temp_templates_db):
        """Prueba obtener todas las plantillas de un lenguaje."""
        loader = TemplateLoader(templates_path=temp_templates_db)
        templates = loader.get_all_templates_for_language('python')
        assert 'requirements.txt' in templates
        assert 'setup.py' in templates

    def test_generate_with_templates(self, temp_templates_db):
        """Prueba la generación con plantillas."""
        loader = TemplateLoader(templates_path=temp_templates_db)
        files = loader.generate_with_templates('python', 'mi_app')
        assert 'requirements.txt' in files
        assert 'setup.py' in files
        # Verificar reemplazo de variables
        assert 'mi_app' in files['setup.py']

    def test_get_build_commands(self, temp_templates_db):
        """Prueba obtener comandos de build."""
        loader = TemplateLoader(templates_path=temp_templates_db)
        commands = loader.get_build_commands('python')
        assert commands['build'] == 'python -m build'

    def test_get_language_from_extension(self, temp_templates_db):
        """Prueba detectar lenguaje por extensión."""
        loader = TemplateLoader(templates_path=temp_templates_db)
        lang = loader.get_language_from_extension('.py')
        assert lang == 'python'
        lang2 = loader.get_language_from_extension('.cpp')
        assert lang2 == 'cpp'
        lang3 = loader.get_language_from_extension('.unknown')
        assert lang3 is None
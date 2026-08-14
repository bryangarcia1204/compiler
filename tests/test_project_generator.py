"""Pruebas para el generador de proyectos con IA."""

import os
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.proyect_editor.project_generator import ProjectGenerator
from src.proyect_editor.template_loader import TemplateLoader


@pytest.fixture
def project_info():
    """Crea información de proyecto de ejemplo."""
    return {
        'project_dir': '/tmp/mi_proyecto',
        'main_language': 'cpp',
        'project_type': 'extension',
        'binary_target': 'pyd',
        'files': [
            {'rel_path': 'main.cpp', 'name': 'main.cpp', 'language': 'cpp', 'content': 'int main() {}'},
            {'rel_path': 'utils.cpp', 'name': 'utils.cpp', 'language': 'cpp', 'content': 'void utils() {}'}
        ],
        'source_files': [
            {'rel_path': 'main.cpp', 'language': 'cpp', 'content': 'int main() {}'},
            {'rel_path': 'utils.cpp', 'language': 'cpp', 'content': 'int main() {}'}
        ],
        'dependencies': {'pybind11', 'setuptools'},
        'main_files': ['main.cpp'],
        'config_files': ['setup.py'],
        'suggested_config_files': ['CMakeLists.txt'],
        'suggested_actions': ['Compilar con setup.py'],
        'languages': {'cpp': 2, 'python': 1},  # evitamos Counter
    }


class TestProjectGenerator:
    """Pruebas para ProjectGenerator."""

    def test_generate_with_templates(self, project_info):
        """Prueba la generación de archivos con plantillas."""
        generator = ProjectGenerator(use_ai=False)
        files = generator._generate_with_templates(
            language='cpp',
            project_name='mi_proyecto',
            project_type='extension',
            project_info=project_info
        )

        assert 'CMakeLists.txt' in files or 'Makefile' in files

    def test_generate_fallback_templates(self, project_info):
        """Prueba las plantillas de fallback."""
        generator = ProjectGenerator(use_ai=False)
        files = generator._generate_fallback_templates(
            language='python',
            project_name='mi_proyecto',
            project_type='extension',
            project_info=project_info
        )

        assert 'requirements.txt' in files
        assert 'setup.py' in files
        assert '.gitignore' in files

    def test_make_setup_py_with_cpp(self, project_info):
        """Prueba la generación de setup.py para C++."""
        generator = ProjectGenerator(use_ai=False)
        setup_content = generator._make_setup_py('mi_proyecto', project_info)

        assert 'pybind11' in setup_content
        assert 'Extension' in setup_content
        assert 'mi_proyecto' in setup_content

    def test_make_setup_py_pure_python(self):
        """Prueba la generación de setup.py para Python puro."""
        generator = ProjectGenerator(use_ai=False)
        info = {'source_files': [{'language': 'python'}]}
        setup_content = generator._make_setup_py('mi_proyecto', info)

        assert 'pybind11' not in setup_content
        assert 'find_packages' in setup_content

    def test_enhance_files_with_ai_mock(self, project_info):
        """Prueba la mejora de archivos con IA usando mock."""
        existing_files = {
            'setup.py': 'from setuptools import setup\nsetup(name="example")'
        }

        mock_response = json.dumps({
            "files": {
                "setup.py": "from setuptools import setup\nimport pybind11\nsetup(name='example', ext_modules=[])"
            },
            "build_command": {
                "cmd": ["python", "setup.py", "build_ext", "--inplace"],
                "cwd": ".",
                "timeout": 300,
                "description": "Compilar extensión"
            }
        })

        generator = ProjectGenerator(
            use_ai=True,
            provider='plataformia',
            api_key='fake'
        )

        with patch.object(generator.ai_client, 'chat', return_value=mock_response):
            result = generator.enhance_files_with_ai(
                project_info,
                existing_files,
                'Mejorar el setup.py'
            )

        assert 'files' in result
        assert 'build_command' in result
        assert 'pybind11' in result['files']['setup.py']
        assert result['build_command']['cmd'] == ['python', 'setup.py', 'build_ext', '--inplace']

    def test_extract_json_from_response(self):
        """Prueba la extracción de JSON del generador."""
        generator = ProjectGenerator(use_ai=False)

        # JSON con el formato esperado
        response = '''```json
{
    "files": {
        "CMakeLists.txt": "cmake_minimum_required..."
    },
    "build_command": {
        "cmd": ["cmake", ".."]
    }
}
```'''
        result = generator._extract_json_from_response(response)
        assert result is not None
        assert '"files"' in result
        assert '"build_command"' in result

        # JSON directo
        response = '{"files": {"test.txt": "content"}, "build_command": null}'
        result = generator._extract_json_from_response(response)
        assert result == response

        # JSON incompleto
        response = '{"files": {}}'
        result = generator._extract_json_from_response(response)
        assert result is not None

    def test_parse_ai_response(self):
        """Prueba el parseo de respuesta de IA en formato de archivos."""
        generator = ProjectGenerator(use_ai=False)

        content = """--- setup.py ---
from setuptools import setup
setup(name='example')
--- FIN ---
--- README.md ---
# Example
--- FIN ---"""

        result = generator._parse_ai_response(content, 'python')
        assert 'setup.py' in result
        assert 'README.md' in result
        assert 'setuptools' in result['setup.py']

    def test_generate_config_files_without_ai(self, project_info):
        """Prueba la generación de archivos sin IA."""
        generator = ProjectGenerator(use_ai=False)
        files = generator.generate_config_files(project_info, '')

        assert isinstance(files, dict)
        # Debe generar al menos .gitignore o algún archivo
        assert len(files) > 0
"""Pruebas para el analizador de proyectos con IA."""

import os
import sys
import tempfile
import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.proyect_editor.project_analyzer import ProjectAnalyzer
from src.ai_client import AIClient


@pytest.fixture
def temp_project_dir():
    """Crea un directorio temporal con archivos de proyecto."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Crear estructura de proyecto C++ con pybind11
        src_dir = os.path.join(tmpdir, 'src')
        os.makedirs(src_dir)
        os.makedirs(os.path.join(tmpdir, 'include'))

        # Archivos fuente
        with open(os.path.join(src_dir, 'main.cpp'), 'w') as f:
            f.write("""#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

int add(int a, int b) { return a + b; }

PYBIND11_MODULE(example, m) {
    m.def("add", &add, "A function that adds two numbers");
}
""")
        with open(os.path.join(src_dir, 'utils.cpp'), 'w') as f:
            f.write("#include <iostream>\nvoid hello() { std::cout << \"Hello\"; }")

        with open(os.path.join(tmpdir, 'setup.py'), 'w') as f:
            f.write("""from setuptools import setup, Extension
import pybind11

ext = Extension('example', sources=['src/main.cpp', 'src/utils.cpp'],
                include_dirs=[pybind11.get_include()],
                language='c++')
setup(name='example', ext_modules=[ext])
""")

        with open(os.path.join(tmpdir, 'requirements.txt'), 'w') as f:
            f.write("pybind11>=2.10\nsetuptools>=64.0")

        yield tmpdir


class TestProjectAnalyzer:
    """Pruebas para ProjectAnalyzer."""

    def test_analyze_cpp_project(self, temp_project_dir):
        """Prueba el análisis de un proyecto C++ con pybind11."""
        analyzer = ProjectAnalyzer(temp_project_dir, use_ai=False)
        summary = analyzer.analyze()

        assert summary['project_dir'] == temp_project_dir
        assert summary['main_language'] == 'cpp'
        assert 'cpp' in summary['languages']
        assert 'python' in summary['languages']
        assert len(summary['source_files']) > 0
        assert 'pybind11' in str(summary['dependencies'])
        assert summary['project_type'] in ['extension', 'library']
        assert summary['intent_confidence'] > 0

    def test_detect_main_files(self, temp_project_dir):
        """Prueba la detección de archivos principales."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._scan_files()
        analyzer._analyze_sources()
        analyzer._detect_main_files()

        main_files = analyzer.summary['main_files']
        assert len(main_files) > 0
        # Debe detectar main.cpp o bindings
        assert any('main.cpp' in f for f in main_files)

    def test_extract_dependencies(self, temp_project_dir):
        """Prueba la extracción de dependencias."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        summary = analyzer.analyze()

        dependencies = summary['dependencies']
        assert 'pybind11' in str(dependencies) or 'pybind11' in dependencies

    def test_prepare_summary_for_ai(self, temp_project_dir):
        """Prueba la preparación del summary para IA."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.analyze()

        summary_for_ai = analyzer._prepare_summary_for_ai(
            include_content=True,
            max_content_size=100
        )

        assert 'dependencies' in summary_for_ai
        assert 'files' in summary_for_ai
        # Verificar que se truncó el contenido
        for file_entry in summary_for_ai['files']:
            if file_entry.get('content'):
                assert len(file_entry['content']) <= 100 + 20  # + por el truncado

    def test_get_ai_suggestions_with_mock(self, temp_project_dir):
        """Prueba la obtención de sugerencias de IA con mock."""
        analyzer = ProjectAnalyzer(
            temp_project_dir,
            use_ai=True,
            provider='deepseek',
            api_key='fake'
        )

        # Mock del AIClient
        mock_response = json.dumps({
            "project_type": "extension",
            "confidence": 0.92,
            "missing_configs": ["CMakeLists.txt"],
            "build_commands": ["python setup.py build_ext --inplace"],
            "recommendations": ["Añadir tests"],
            "binary_target": "pyd"
        })

        with patch.object(analyzer.ai_client, 'chat', return_value=mock_response):
            analyzer._get_ai_suggestions()

        assert 'ai_suggestions' in analyzer.summary
        assert analyzer.summary['ai_suggestions']['project_type'] == 'extension'
        assert 'CMakeLists.txt' in analyzer.summary['suggested_config_files']

    def test_get_ai_veredict(self, temp_project_dir):
        """Prueba la obtención del veredicto de IA."""
        analyzer = ProjectAnalyzer(
            temp_project_dir,
            use_ai=True,
            provider='plataformia',
            api_key='fake'
        )
        analyzer.analyze()

        # Mock de respuesta
        mock_veredict = json.dumps({
            "project_type": "extension",
            "main_language": "cpp",
            "intent_confidence": 0.95,
            "suggested_config_files": ["CMakeLists.txt", "Makefile"],
            "suggested_actions": ["Compilar con CMake", "Ejecutar pruebas"]
        })

        with patch.object(analyzer.ai_client, 'chat', return_value=mock_veredict):
            veredict = analyzer.get_ai_veredict()

        assert veredict is not None
        assert veredict['project_type'] == 'extension'
        assert veredict['intent_confidence'] == 0.95

    def test_extract_json_from_response(self, temp_project_dir):
        """Prueba la extracción de JSON de respuestas de IA."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        # Caso 1: JSON puro
        response = '{"project_type": "extension", "confidence": 0.9}'
        result = analyzer._extract_json_from_response(response)
        assert result == response

        # Caso 2: JSON en bloque markdown
        response = '```json\n{"project_type": "extension"}\n```'
        result = analyzer._extract_json_from_response(response)
        assert 'project_type' in result

        # Caso 3: JSON con texto adicional
        response = 'Aquí está el JSON: {"project_type": "extension"}'
        result = analyzer._extract_json_from_response(response)
        assert 'project_type' in result

        # Caso 4: JSON mal formado -> None
        response = 'Este no es JSON'
        result = analyzer._extract_json_from_response(response)
        assert result is None

    def test_get_summary_string(self, temp_project_dir):
        """Prueba la generación del resumen legible."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.analyze()
        summary_str = analyzer.get_summary()

        assert '📁' in summary_str
        assert '📝' in summary_str
        assert temp_project_dir in summary_str
        assert 'Dependencias detectadas' in summary_str
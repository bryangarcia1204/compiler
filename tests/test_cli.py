"""Pruebas para la interfaz de línea de comandos."""

import os
import sys
import tempfile
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.cli import main, list_tools, compile_file, package_file
from argparse import Namespace


class TestCLI:
    """Pruebas para la CLI."""

    def test_list_tools(self, capsys):
        """Prueba el comando list-tools."""
        with patch('src.cli.CompilerDetector.get_all_tools') as mock_get:
            mock_get.return_value = [
                {'name': 'GCC', 'version': '11.2.0', 'type': 'compiler', 'extensions': ['.c', '.cpp']}
            ]
            list_tools()
            captured = capsys.readouterr()
            assert 'GCC' in captured.out
            assert 'compiler' in captured.out

    def test_list_tools_empty(self, capsys):
        """Prueba list-tools cuando no hay herramientas."""
        with patch('src.cli.CompilerDetector.get_all_tools') as mock_get:
            mock_get.return_value = []
            list_tools()
            captured = capsys.readouterr()
            assert 'No se detectaron herramientas' in captured.out

    def test_compile_file_success(self):
        """Prueba la compilación exitosa."""
        args = Namespace(
            file='test.c',
            tool='gcc',
            output='test.exe',
            type='exe',
            release=False,
            args='-Wall'
        )

        with patch('os.path.isfile', return_value=True), \
             patch('src.cli.CompilerDetector') as mock_detector, \
             patch('src.cli.CompilationEngine') as mock_engine:

            mock_tool = {'name': 'gcc'}
            mock_detector.return_value.get_all_tools.return_value = [mock_tool]
            mock_detector.return_value.get_tool_for_file.return_value = mock_tool

            mock_engine.return_value.compile.return_value = {
                'success': True,
                'stdout': 'OK',
                'stderr': '',
                'returncode': 0,
                'output_file': 'test.exe'
            }

            with patch('sys.exit') as mock_exit:
                compile_file(args)
                mock_exit.assert_called_with(0)

    def test_compile_file_failure(self):
        """Prueba la compilación fallida."""
        args = Namespace(
            file='test.c',
            tool=None,
            output=None,
            type='exe',
            release=False,
            args=None
        )

        with patch('os.path.isfile', return_value=True), \
             patch('src.cli.CompilerDetector') as mock_detector, \
             patch('src.cli.CompilationEngine') as mock_engine:

            mock_tool = {'name': 'gcc'}
            mock_detector.return_value.get_tool_for_file.return_value = mock_tool

            mock_engine.return_value.compile.return_value = {
                'success': False,
                'stdout': '',
                'stderr': 'Error de compilación',
                'returncode': 1,
                'output_file': None
            }

            with patch('sys.exit') as mock_exit:
                compile_file(args)
                mock_exit.assert_called_with(1)

    def test_compile_file_not_found(self):
        """Prueba cuando el archivo no existe."""
        args = Namespace(file='noexiste.c',
                        tool=None,
                        output=None,
                        type=None,
                        release=False,
                        args=None)
        with patch('os.path.isfile', return_value=False):
            with patch('sys.exit') as mock_exit:
                compile_file(args)
                mock_exit.assert_called_with(1)

    def test_package_file_success(self):
        """Prueba el empaquetado exitoso."""
        args = Namespace(
            file='script.py',
            tool='pyinstaller',
            output='dist/app',
            args=None
        )

        with patch('os.path.isfile', return_value=True), \
             patch('src.cli.CompilerDetector') as mock_detector, \
             patch('src.cli.CompilationEngine') as mock_engine:

            mock_tool = {'name': 'PyInstaller', 'type': 'packager'}
            mock_detector.return_value.get_all_tools.return_value = [mock_tool]

            mock_engine.return_value.package.return_value = {
                'success': True,
                'stdout': 'OK',
                'stderr': '',
                'returncode': 0,
                'output_file': 'dist/app'
            }

            with patch('sys.exit') as mock_exit:
                package_file(args)
                mock_exit.assert_called_with(0)

    def test_package_file_no_packager(self):
        """Prueba cuando no hay empaquetador."""
        args = Namespace(file='script.py', tool=None, output=None, args=None)

        with patch('os.path.isfile', return_value=True), \
            patch('src.cli.CompilerDetector') as mock_detector, \
            patch('sys.exit') as mock_exit, \
            patch('sys.stderr'):

            mock_detector.return_value.get_all_tools.return_value = []
            mock_detector.return_value.get_tool_for_file.return_value = None

            # Hacer que sys.exit lance SystemExit para detener la ejecución
            mock_exit.side_effect = SystemExit

            with pytest.raises(SystemExit):
                package_file(args)
            mock_exit.assert_called_with(1)

    def test_cli_main_analyze(self):
        """Prueba el comando analyze desde main."""
        args = ['compilador-cli', 'analyze', '/tmp']
        with patch('sys.argv', args), \
             patch('src.cli.analyze_project') as mock_analyze:
            main()
            mock_analyze.assert_called_once()

    def test_cli_main_generate(self):
        """Prueba el comando generate desde main."""
        args = ['compilador-cli', 'generate', '/tmp']
        with patch('sys.argv', args), \
             patch('src.cli.generate_files') as mock_generate:
            main()
            mock_generate.assert_called_once()

    def test_cli_main_enhance(self):
        """Prueba el comando enhance desde main."""
        args = ['compilador-cli', 'enhance', '/tmp', '--ai']
        with patch('sys.argv', args), \
             patch('src.cli.enhance_files') as mock_enhance:
            main()
            mock_enhance.assert_called_once()
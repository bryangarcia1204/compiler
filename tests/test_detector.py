"""Pruebas unitarias para el detector de compiladores."""
import unittest
import sys
import os
import platform
from unittest.mock import patch, MagicMock

# Añadir src al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detector.compiler_detector import CompilerDetector, _get_python_cmd, _get_version
from src.detector.language_detector import LanguageDetector
from src.utils.error_parser import ErrorParser
from src.utils.argument_suggester import ArgumentSuggester
from src.utils.output_types import OUTPUT_TYPE_MAP


class TestCompilerDetector(unittest.TestCase):
    """Pruebas para el detector de compiladores."""

    def test_get_python_cmd(self):
        """Verifica que detecta el comando Python correctamente."""
        cmd = _get_python_cmd()
        if platform.system() == 'Windows':
            self.assertIn(cmd, ['python', 'python3', None])
        else:
            # En Linux/macOS debería priorizar python3
            if cmd is not None:
                self.assertEqual(cmd, 'python3')

    def test_get_all_tools_returns_list(self):
        """Verifica que get_all_tools siempre retorna una lista."""
        tools = CompilerDetector.get_all_tools()
        self.assertIsInstance(tools, list)

    def test_get_all_tools_cached(self):
        """Verifica que la caché funciona correctamente."""
        # Primera llamada
        tools1 = CompilerDetector.get_all_tools()
        # Segunda llamada (debería usar caché)
        tools2 = CompilerDetector.get_all_tools()
        # No debería ser la misma referencia, pero sí igual contenido
        self.assertEqual(tools1, tools2)

    def test_get_python_cmd_with_which(self):
        """Prueba la detección de Python con shutil.which."""
        # Este test es simple: verifica que la función existe y retorna algo válido
        cmd = _get_python_cmd()
        # En cualquier sistema debería retornar 'python', 'python3' o None
        self.assertIn(cmd, ['python', 'python3', None])

    def test_get_tool_output_capabilities(self):
        """Verifica que retorna capacidades válidas para cada herramienta."""
        test_cases = [
            ({'name': 'gcc', 'type': 'compiler'}, ['exe', 'bin', 'dll', 'so']),
            ({'name': 'pyinstaller', 'type': 'packager'}, ['exe', 'bin']),
            ({'name': 'herramienta_desconocida', 'type': 'compiler'}, ['exe', 'bin', 'dll', 'so', 'dylib', 'a', 'lib', 'obj', 'pyd', 'wasm']),
            ({'name': 'otra_desconocida', 'type': 'packager'}, ['exe', 'bin']),
            ({'name': 'otra_mas', 'type': 'interpreter'}, []),
        ]

        for tool, expected_contains in test_cases:
            caps = CompilerDetector.get_tool_output_capabilities(tool)
            self.assertIsInstance(caps, list)
            # Verificar que al menos algunos de los esperados están en la lista
            found = any(exp in caps for exp in expected_contains)
            if expected_contains:  # Si hay elementos esperados
                self.assertTrue(found)

    def test_filter_tools_by_language(self):
        """Verifica el filtrado de herramientas por extensión."""
        tools = [
            {'name': 'GCC', 'extensions': ['.c', '.cpp'], 'type': 'compiler'},
            {'name': 'Python', 'extensions': ['.py'], 'type': 'interpreter'},
            {'name': 'Node', 'extensions': ['.js'], 'type': 'interpreter'},
        ]

        # Filtrar por extensión .py
        filtered = CompilerDetector.filter_tools_by_language(tools, '.py')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['name'], 'Python')

        # Filtrar por extensión .c
        filtered = CompilerDetector.filter_tools_by_language(tools, '.c')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['name'], 'GCC')

        # Filtrar por extensión inexistente
        filtered = CompilerDetector.filter_tools_by_language(tools, '.rb')
        self.assertEqual(len(filtered), 0)

    def test_get_installation_suggestion(self):
        """Verifica que retorna sugerencias para herramientas conocidas."""
        # Herramientas conocidas
        self.assertIsNotNone(CompilerDetector.get_installation_suggestion('PyInstaller'))
        self.assertIsNotNone(CompilerDetector.get_installation_suggestion('cargo'))
        self.assertIsNotNone(CompilerDetector.get_installation_suggestion('go'))
        
        # Herramienta desconocida (debería retornar un mensaje genérico)
        suggestion = CompilerDetector.get_installation_suggestion('herramienta_inexistente')
        self.assertIn('Instalar', suggestion)


class TestLanguageDetector(unittest.TestCase):
    """Pruebas para el detector de lenguajes."""

    def test_detect_known_languages(self):
        """Verifica la detección de lenguajes conocidos."""
        test_cases = [
            ('archivo.c', 'C', 'compiler'),
            ('archivo.cpp', 'C++', 'compiler'),
            ('archivo.java', 'Java', 'compiler'),
            ('archivo.py', 'Python', 'interpreter'),
            ('archivo.js', 'JavaScript', 'interpreter'),
            ('archivo.go', 'Go', 'compiler'),
            ('archivo.rs', 'Rust', 'compiler'),
            ('archivo.cs', 'C#', 'compiler'),
        ]

        for filename, expected_lang, expected_type in test_cases:
            result = LanguageDetector.detect(filename)
            self.assertIsNotNone(result)
            self.assertEqual(result['language'], expected_lang)
            self.assertEqual(result['type'], expected_type)

    def test_detect_unknown_language(self):
        """Verifica que retorna None para lenguajes desconocidos."""
        result = LanguageDetector.detect('archivo.xyz')
        self.assertIsNone(result)

        result = LanguageDetector.detect('sin_extension')
        self.assertIsNone(result)

    def test_is_compiled(self):
        """Verifica la detección de lenguajes compilados."""
        self.assertTrue(LanguageDetector.is_compiled('archivo.c'))
        self.assertTrue(LanguageDetector.is_compiled('archivo.cpp'))
        self.assertTrue(LanguageDetector.is_compiled('archivo.java'))
        self.assertTrue(LanguageDetector.is_compiled('archivo.go'))
        self.assertTrue(LanguageDetector.is_compiled('archivo.rs'))
        
        self.assertFalse(LanguageDetector.is_compiled('archivo.py'))
        self.assertFalse(LanguageDetector.is_compiled('archivo.js'))
        self.assertFalse(LanguageDetector.is_compiled('archivo.rb'))

    def test_is_interpreted(self):
        """Verifica la detección de lenguajes interpretados."""
        self.assertTrue(LanguageDetector.is_interpreted('archivo.py'))
        self.assertTrue(LanguageDetector.is_interpreted('archivo.js'))
        self.assertTrue(LanguageDetector.is_interpreted('archivo.rb'))
        self.assertTrue(LanguageDetector.is_interpreted('archivo.php'))
        
        self.assertFalse(LanguageDetector.is_interpreted('archivo.c'))
        self.assertFalse(LanguageDetector.is_interpreted('archivo.cpp'))
        self.assertFalse(LanguageDetector.is_interpreted('archivo.java'))

    def test_allowed_outputs(self):
        """Verifica que cada lenguaje tiene outputs permitidos."""
        for ext, info in LanguageDetector.LANGUAGE_MAP.items():
            self.assertIn('default_outputs', info)
            self.assertIsInstance(info['default_outputs'], list)
            self.assertGreater(len(info['default_outputs']), 0)


class TestErrorParser(unittest.TestCase):
    """Pruebas para el parser de errores."""

    def test_parse_gcc_error(self):
        """Prueba el parseo de errores de GCC."""
        stderr = """archivo.c:10:5: error: 'x' undeclared (first use in this function)
archivo.c:15:3: warning: implicit declaration of function 'printf'
"""
        errors = ErrorParser.parse('gcc', stderr)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['file'], 'archivo.c')
        self.assertEqual(errors[0]['line'], 10)
        self.assertEqual(errors[0]['level'], 'error')

    def test_parse_clang_error(self):
        """Prueba el parseo de errores de Clang."""
        stderr = """archivo.c:10:5: error: use of undeclared identifier 'x'
archivo.c:15:3: warning: implicit declaration of function 'printf'
"""
        errors = ErrorParser.parse('clang', stderr)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['file'], 'archivo.c')
        self.assertEqual(errors[0]['line'], 10)
        self.assertEqual(errors[0]['level'], 'error')

    def test_parse_javac_error(self):
        """Prueba el parseo de errores de Javac."""
        stderr = """Main.java:10: error: cannot find symbol
Main.java:15: warning: [unchecked] unchecked conversion
"""
        errors = ErrorParser.parse('javac', stderr)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['file'], 'Main.java')
        self.assertEqual(errors[0]['line'], 10)
        self.assertEqual(errors[0]['level'], 'error')

    def test_parse_python_error(self):
        """Prueba el parseo de errores de Python."""
        stderr = """Traceback (most recent call last):
  File "main.py", line 10, in <module>
    import missing_module
ModuleNotFoundError: No module named 'missing_module'
"""
        errors = ErrorParser.parse('python', stderr)
        self.assertGreater(len(errors), 0)
        # Verificar que al menos hay errores parseados
        # El parser puede devolver errores 'raw' si el patrón no matchea exactamente
        self.assertTrue(len(errors) > 0)

    def test_parse_empty_stderr(self):
        """Verifica que retorna lista vacía para stderr vacío."""
        errors = ErrorParser.parse('gcc', '')
        self.assertEqual(errors, [])

    def test_format_error(self):
        """Prueba el formateo de errores."""
        error = {
            'file': 'main.c',
            'line': 10,
            'column': 5,
            'level': 'error',
            'message': 'Syntax error'
        }
        formatted = ErrorParser.format_error(error)
        self.assertIn('main.c:10:5', formatted)
        self.assertIn('[ERROR]', formatted)
        self.assertIn('Syntax error', formatted)

        # Error raw
        error = {'raw': 'Error message'}
        formatted = ErrorParser.format_error(error)
        self.assertEqual(formatted, 'Error message')


class TestArgumentSuggester(unittest.TestCase):
    """Pruebas para el sugeridor de argumentos."""

    def test_get_arguments_for_tool_exact_match(self):
        """Verifica que retorna argumentos para herramientas exactas."""
        args = ArgumentSuggester.get_arguments_for_tool('gcc')
        self.assertIsInstance(args, list)
        self.assertGreater(len(args), 0)
        self.assertTrue(any(a['flag'] == '-O2' for a in args))

        args = ArgumentSuggester.get_arguments_for_tool('cargo')
        self.assertIsInstance(args, list)
        self.assertGreater(len(args), 0)
        self.assertTrue(any(a['flag'] == '--release' for a in args))

    def test_get_arguments_for_tool_partial_match(self):
        """Verifica el fallback para herramientas similares."""
        # GCC para compiladores similares
        args = ArgumentSuggester.get_arguments_for_tool('clang')
        self.assertIsInstance(args, list)
        self.assertGreater(len(args), 0)

        # Cargo para Rust
        args = ArgumentSuggester.get_arguments_for_tool('rustc')
        self.assertIsInstance(args, list)
        self.assertGreater(len(args), 0)

    def test_get_arguments_for_tool_unknown(self):
        """Verifica que retorna lista vacía para herramientas desconocidas."""
        args = ArgumentSuggester.get_arguments_for_tool('herramienta_inexistente')
        self.assertEqual(args, [])

    def test_arguments_have_required_fields(self):
        """Verifica que todos los argumentos tienen los campos requeridos."""
        for tool_name, args in ArgumentSuggester.ARGUMENTS.items():
            for arg in args:
                self.assertIn('flag', arg)
                self.assertIn('description', arg)
                self.assertIn('category', arg)


class TestOutputTypes(unittest.TestCase):
    """Pruebas para el mapa de tipos de salida."""

    def test_output_type_map_has_values(self):
        """Verifica que el mapa de tipos de salida tiene contenido."""
        self.assertGreater(len(OUTPUT_TYPE_MAP), 0)
        for key, value in OUTPUT_TYPE_MAP.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, str)

    def test_common_output_types_exist(self):
        """Verifica que los tipos de salida comunes existen."""
        self.assertIn('Ejecutable (.exe)', OUTPUT_TYPE_MAP)
        self.assertIn('Biblioteca dinámica Windows (.dll)', OUTPUT_TYPE_MAP)
        self.assertIn('Módulo Python (.pyd/.so)', OUTPUT_TYPE_MAP)
        self.assertIn('WebAssembly (.wasm)', OUTPUT_TYPE_MAP)


class TestCompilationEngine(unittest.TestCase):
    """Pruebas para el motor de compilación."""

    def setUp(self):
        """Configuración antes de cada prueba."""
        from src.engine.compilation_engine import CompilationEngine
        self.engine = CompilationEngine()

    def test_build_command_for_interpreter(self):
        """Prueba la construcción de comandos para intérpretes."""
        tool = {'type': 'interpreter', 'command': 'python'}
        cmd, cwd, actions = self.engine.build_command_for(
            'main.py', tool, output_type=None
        )
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd[0], 'python')
        self.assertEqual(cmd[1], 'main.py')

    def test_build_command_for_compiler_fallback(self):
        """Prueba el fallback para compiladores."""
        tool = {'type': 'compiler', 'command': 'gcc'}
        cmd, cwd, actions = self.engine.build_command_for(
            'main.c', tool, output_type='exe'
        )
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd[0], 'gcc')

    def test_build_command_for_go(self):
        """Prueba la construcción de comandos para Go."""
        tool = {'type': 'compiler', 'name': 'go'}
        cmd, cwd, actions, env = self.engine.build_command_for(
            'main.go', tool, release_mode=True
        )
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd[0], 'go')
        self.assertIn('-ldflags', cmd)

    def test_build_package_command_pyinstaller(self):
        """Prueba la construcción de comandos para PyInstaller."""
        tool = {'name': 'pyinstaller', 'command': 'python'}
        cmd, cwd, actions = self.engine.build_package_command(
            'main.py', tool
        )
        self.assertIsNotNone(cmd)
        self.assertIn('pyinstaller', cmd)
        self.assertIn('--onefile', cmd)

    def test_build_package_command_unknown(self):
        """Verifica que lanza excepción para herramientas desconocidas."""
        tool = {'name': 'herramienta_desconocida'}
        with self.assertRaises(ValueError):
            self.engine.build_package_command('main.py', tool)

# Añadir al final de test_detector.py

class TestCompilerDetectorAdvanced(unittest.TestCase):
    """Pruebas adicionales para el detector."""

    @patch('shutil.which')
    def test_get_all_tools_with_mocks(self, mock_which):
        """Simula la detección de herramientas con mocks."""
        # Simular que todas las herramientas están disponibles
        mock_which.return_value = '/usr/bin/gcc'
        tools = CompilerDetector.get_all_tools(force_refresh=True)
        # Debería haber al menos una herramienta (gcc) aunque otros mocks no están
        self.assertGreater(len(tools), 0)

    def test_caching(self):
        """Verifica que la caché evita detecciones repetidas."""
        # Primera llamada
        tools1 = CompilerDetector.get_all_tools()
        # Segunda llamada (debería usar caché)
        with patch('src.detector.compiler_detector._get_version') as mock_version:
            # No debería llamarse a _get_version si usa caché
            tools2 = CompilerDetector.get_all_tools()
            mock_version.assert_not_called()
        self.assertEqual(tools1, tools2)

    def test_force_refresh(self):
        """Verifica que force_refresh invalida la caché."""
        with patch('src.detector.compiler_detector._get_version') as mock_version:
            # Primera llamada con force_refresh=True
            CompilerDetector.get_all_tools(force_refresh=True)
            # Debería haberse llamado a _get_version al menos una vez
            self.assertTrue(mock_version.called)
            mock_version.reset_mock()
            # Segunda llamada sin force_refresh debería usar caché
            CompilerDetector.get_all_tools(force_refresh=False)
            mock_version.assert_not_called()

    @patch('threading.Event')
    def test_concurrent_detection(self, mock_event):
        """Simula detección concurrente para probar el bloqueo."""
        # Hacer que _detecting sea True para simular otra detección en curso
        CompilerDetector._detecting = True
        # Llamar a get_all_tools debería esperar y luego retornar caché
        with patch.object(CompilerDetector, '_cached_tools', [{'name': 'dummy'}]):
            tools = CompilerDetector.get_all_tools()
            self.assertEqual(tools, [{'name': 'dummy'}])
            # Verificar que se llamó a Event().wait
            mock_event.return_value.wait.assert_called()
        CompilerDetector._detecting = False

if __name__ == '__main__':
    unittest.main()
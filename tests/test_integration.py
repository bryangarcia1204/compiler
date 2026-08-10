"""Pruebas de integración para el compilador profesional."""
import unittest
import os
import sys
import tempfile
import shutil

# Añadir src al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestIntegration(unittest.TestCase):
    """Pruebas de integración del sistema completo."""

    def test_language_detection_integration(self):
        """Prueba la detección de lenguaje con archivos reales."""
        from src.language_detector import LanguageDetector
        
        # Crear archivos temporales con delete=False y cerrar explícitamente
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(b'print("Hello World")')
            f.flush()
            f.close()  # Cerrar explícitamente para liberar el archivo en Windows
            result = LanguageDetector.detect(f.name)
            self.assertEqual(result['language'], 'Python')
            os.unlink(f.name)

        with tempfile.NamedTemporaryFile(suffix='.c', delete=False) as f:
            f.write(b'int main() { return 0; }')
            f.flush()
            f.close()
            result = LanguageDetector.detect(f.name)
            self.assertEqual(result['language'], 'C')
            os.unlink(f.name)

    def test_error_parser_integration(self):
        """Prueba el parser de errores con salida real de compilación."""
        from src.error_parser import ErrorParser
        
        # Simular salida de GCC
        gcc_output = """main.c:10:5: error: 'x' undeclared (first use in this function)
main.c:15:3: warning: implicit declaration of function 'printf'"""
        
        errors = ErrorParser.parse('gcc', gcc_output)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['file'], 'main.c')

    def test_argument_suggester_integration(self):
        """Prueba el sugeridor de argumentos con herramientas reales."""
        from src.argument_suggester import ArgumentSuggester
        
        # GCC debería tener argumentos
        gcc_args = ArgumentSuggester.get_arguments_for_tool('gcc')
        self.assertGreater(len(gcc_args), 10)
        
        # PyInstaller debería tener argumentos
        pyinstaller_args = ArgumentSuggester.get_arguments_for_tool('pyinstaller')
        self.assertGreater(len(pyinstaller_args), 5)


if __name__ == '__main__':
    unittest.main()
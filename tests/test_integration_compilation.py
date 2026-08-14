"""Pruebas de integración: compilación de archivos reales."""
import unittest
import os
import sys
import tempfile
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.compilation_engine import CompilationEngine
from src.compiler_detector import CompilerDetector


class TestIntegrationCompilation(unittest.TestCase):
    """Pruebas de integración que compilan archivos reales."""

    @classmethod
    def setUpClass(cls):
        cls.engine = CompilationEngine()
        cls.detector = CompilerDetector()
        cls.fixtures_dir = Path(__file__).parent / 'fixtures'
        cls.fixtures_dir.mkdir(exist_ok=True)
        cls._create_fixtures()
        # Obtener herramientas disponibles una vez
        cls.available_tools = cls.detector.get_all_tools()

    @classmethod
    def _create_fixtures(cls):
        fixtures = {
            'hello.c': '#include <stdio.h>\nint main() { printf("Hello, World!\\n"); return 0; }\n',
            'hello.cpp': '#include <iostream>\nint main() { std::cout << "Hello, C++!\\n"; return 0; }\n',
            'hello.rs': 'fn main() { println!("Hello, Rust!"); }\n',
            'hello.go': 'package main\nimport "fmt"\nfunc main() { fmt.Println("Hello, Go!") }\n',
            'hello.py': 'print("Hello, Python!")\n',
            'hello.js': 'console.log("Hello, JavaScript!");\n',
        }
        for filename, content in fixtures.items():
            filepath = cls.fixtures_dir / filename
            if not filepath.exists():
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

    def _compile_and_run(self, file_name, expected_output, tool_name=None, lang_type=None, timeout=10):
        file_path = self.fixtures_dir / file_name
        self.assertTrue(file_path.exists(), f"Fixture {file_path} no existe")

        # 1. Buscar herramienta
        if tool_name is None:
            ext = file_path.suffix
            filtered = self.detector.filter_tools_by_language(self.available_tools, ext, lang_type)
            if not filtered:
                self.skipTest(f"No hay herramienta disponible para {file_name}")
            tool_info = filtered[0]
            tool_name = tool_info['name']

        tool = next((t for t in self.available_tools if t.get('name', '').lower() == tool_name.lower()), None)
        if not tool:
            self.skipTest(f"Herramienta {tool_name} no disponible")

        # 2. Verificar que el comando existe en el PATH
        import shutil
        command = tool.get('command', '')
        if not shutil.which(command):
            self.skipTest(f"Comando '{command}' no encontrado en el PATH")

        output_dir = tempfile.mkdtemp()
        try:
            output_ext = '.exe' if os.name == 'nt' else ''
            output_file = os.path.join(output_dir, 'output' + output_ext)

            # 3. Intentar compilar
            try:
                result = self.engine.compile(
                    file_path=str(file_path),
                    tool=tool,
                    output_path=output_file,
                    extra_args=[],
                    output_type='exe',
                    release_mode=False
                )
            except FileNotFoundError as e:
                self.skipTest(f"Herramienta '{command}' no disponible: {e}")

            # 4. Detectar errores de comando no encontrado en el stderr
            stderr = result.get('stderr', '')
            if not result['success'] and (
                'No such file' in stderr or
                'not found' in stderr or
                'WinError 2' in stderr or
                'cannot find' in stderr.lower()
            ):
                self.skipTest(f"Herramienta {tool_name} no está disponible en el PATH")

            self.assertTrue(result['success'], f"Compilación falló: {stderr}")

            output_file = result.get('output_file')
            self.assertIsNotNone(output_file, "No se generó archivo de salida")
            self.assertTrue(os.path.exists(output_file), f"Ejecutable no generado: {output_file}")

            proc = subprocess.run(
                [output_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            self.assertEqual(proc.returncode, 0, f"Ejecución falló: {proc.stderr}")
            self.assertIn(expected_output, proc.stdout)

        finally:
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_compile_c(self):
        self._compile_and_run('hello.c', 'Hello, World!', 'gcc', 'compiler')

    def test_compile_cpp(self):
        self._compile_and_run('hello.cpp', 'Hello, C++!', 'g++', 'compiler')

    def test_compile_go(self):
        self._compile_and_run('hello.go', 'Hello, Go!', 'go', 'compiler')

    def test_run_python(self):
        file_path = self.fixtures_dir / 'hello.py'
        output_dir = tempfile.mkdtemp()
        try:
            tool = next((t for t in self.available_tools if t.get('name', '').lower() == 'python'), None)
            if not tool:
                self.skipTest("Python no disponible")
            result = self.engine.compile(
                file_path=str(file_path),
                tool=tool,
                output_path=None,
                extra_args=[],
                output_type=None,
                release_mode=False
            )
            self.assertTrue(result['success'], f"Ejecución falló: {result.get('stderr', '')}")
            self.assertIn('Hello, Python!', result.get('stdout', ''))
        finally:
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
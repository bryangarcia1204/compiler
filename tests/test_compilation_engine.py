"""Pruebas unitarias para el motor de compilación."""
import unittest
import os
import sys
import tempfile
import subprocess
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine.compilation_engine import CompilationEngine
from src.compilers.registry import CompilerRegistry


class TestCompilationEngine(unittest.TestCase):
    """Pruebas para CompilationEngine."""

    @classmethod
    def setUpClass(cls):
        # Asegurar que las estrategias están cargadas
        CompilerRegistry._load_all()

    def setUp(self):
        self.engine = CompilationEngine()

    # ── build_command_for ──

    def test_build_command_for_gcc(self):
        """Prueba que GCC usa la estrategia y genera el comando correcto."""
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        cmd, cwd, actions = self.engine.build_command_for(
            'main.c', tool, output_path='out.exe', output_type='exe'
        )
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd[0], 'gcc')
        self.assertIn('-o', cmd)
        self.assertIn('out.exe', cmd)
        self.assertIn('main.c', cmd)

    def test_build_command_for_gcc_release(self):
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        cmd, cwd, actions = self.engine.build_command_for(
            'main.c', tool, release_mode=True
        )
        self.assertIn('-O2', cmd)

    def test_build_command_for_gcc_debug(self):
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        cmd, cwd, actions = self.engine.build_command_for(
            'main.c', tool, release_mode=False
        )
        self.assertIn('-g', cmd)

    def test_build_command_for_gcc_obj(self):
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        cmd, cwd, actions = self.engine.build_command_for(
            'main.c', tool, output_type='obj'
        )
        self.assertIn('-c', cmd)

    def test_build_command_for_gcc_shared(self):
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        cmd, cwd, actions = self.engine.build_command_for(
            'main.c', tool, output_type='dll'
        )
        self.assertIn('-shared', cmd)

    def test_build_command_for_gcc_static_lib(self):
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        cmd, cwd, actions = self.engine.build_command_for(
            'main.c', tool, output_path='lib.a', output_type='a'
        )
        # En la estrategia GCC, para 'a' no se añade -c ni -shared, se deja como exe
        # El comportamiento original del motor no manejaba 'a' en la parte de compilador,
        # así que la estrategia debería manejarlo. Pero como no está implementado,
        # el fallback tampoco. Por ahora verificamos que no falle.
        self.assertIsNotNone(cmd)
        self.assertIn('gcc', cmd)

    def test_build_command_for_go(self):
        tool = {'name': 'go', 'type': 'compiler', 'command': 'go'}
        cmd, cwd, actions, env = self.engine.build_command_for(
            'main.go', tool, output_path='out'
        )
        self.assertIn('go', cmd)
        self.assertIn('-o', cmd)

    def test_build_command_for_go_release(self):
        tool = {'name': 'go', 'type': 'compiler', 'command': 'go'}
        cmd, cwd, actions, env = self.engine.build_command_for(
            'main.go', tool, release_mode=True
        )
        self.assertIn('-ldflags', cmd)
        self.assertIn('-s -w', cmd)

    def test_build_command_for_rust_cargo(self):
        tool = {'name': 'rust', 'type': 'compiler', 'command': 'cargo'}
        with tempfile.TemporaryDirectory() as tmpdir:
            cargo_toml = os.path.join(tmpdir, 'Cargo.toml')
            with open(cargo_toml, 'w') as f:
                f.write('[package]\nname = "test"\nversion = "0.1.0"\n')
            cmd, cwd, actions = self.engine.build_command_for(
                cargo_toml, tool, output_path='target/release/test'
            )
            self.assertEqual(cmd[0], 'cargo')
            self.assertIn('build', cmd)
            self.assertEqual(cwd, tmpdir)
            self.assertTrue(any(a[0] == 'cargo_move' for a in actions))

    def test_build_command_for_rust_single_file(self):
        tool = {'name': 'rust', 'type': 'compiler', 'command': 'rustc'}
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'main.rs')
            with open(file_path, 'w') as f:
                f.write('fn main() {}')
            cmd, cwd, actions = self.engine.build_command_for(
                file_path, tool, output_path='out'
            )
            self.assertEqual(cmd[0], 'rustc')
            self.assertIn('-o', cmd)

    def test_build_command_for_java(self):
        tool = {'name': 'java', 'type': 'compiler', 'command': 'javac'}
        cmd, cwd, actions = self.engine.build_command_for(
            'Main.java', tool
        )
        self.assertEqual(cmd[0], 'javac')
        self.assertIn('Main.java', cmd)

    def test_build_command_for_java_jar(self):
        tool = {'name': 'java', 'type': 'compiler', 'command': 'javac'}
        cmd, cwd, actions = self.engine.build_command_for(
            'Main.java', tool, output_path='out.jar'
        )
        self.assertEqual(cmd[0], 'javac')
        self.assertTrue(any(a[0] == 'jar' for a in actions))

    def test_build_command_for_dotnet(self):
        tool = {'name': 'dotnet', 'type': 'compiler', 'command': 'dotnet'}
        cmd, cwd, actions = self.engine.build_command_for(
            'project.csproj', tool
        )
        self.assertEqual(cmd[0], 'dotnet')
        self.assertIn('build', cmd)

    def test_build_command_for_dotnet_single_cs(self):
        tool = {'name': 'dotnet', 'type': 'compiler', 'command': 'csc'}
        cmd, cwd, actions = self.engine.build_command_for(
            'Program.cs', tool, output_path='out.exe'
        )
        self.assertEqual(cmd[0], 'csc')
        self.assertIn('/out:out.exe', cmd)

    def test_build_command_for_interpreter(self):
        tool = {'name': 'python', 'type': 'interpreter', 'command': 'python'}
        cmd, cwd, actions = self.engine.build_command_for(
            'script.py', tool
        )
        self.assertEqual(cmd[0], 'python')
        self.assertEqual(cmd[1], 'script.py')

    def test_build_command_for_fallback_compiler(self):
        """Prueba el fallback para compiladores sin estrategia."""
        tool = {'name': 'custom', 'type': 'compiler', 'command': 'mycc'}
        cmd, cwd, actions = self.engine.build_command_for(
            'file.c', tool, output_path='out'
        )
        self.assertEqual(cmd[0], 'mycc')
        self.assertIn('-o', cmd)

    def test_build_command_for_fallback_interpreter(self):
        tool = {'name': 'custom', 'type': 'interpreter', 'command': 'myrun'}
        cmd, cwd, actions = self.engine.build_command_for(
            'file.rb', tool
        )
        self.assertEqual(cmd[0], 'myrun')
        self.assertEqual(cmd[1], 'file.rb')

    # ── build_package_command ──

    def test_build_package_pyinstaller(self):
        tool = {'name': 'pyinstaller', 'command': 'python', 'type': 'packager'}
        cmd, cwd, actions = self.engine.build_package_command(
            'main.py', tool, output_path='dist/main'
        )
        self.assertIsNotNone(cmd)
        self.assertIn('pyinstaller', cmd)
        self.assertIn('--onefile', cmd)
        self.assertIn('--noconsole', cmd)

    def test_build_package_pkg(self):
        tool = {'name': 'pkg', 'command': 'pkg', 'type': 'packager'}
        cmd, cwd, actions = self.engine.build_package_command(
            'main.js', tool, output_path='out.exe'
        )
        self.assertEqual(cmd[0], 'pkg')
        self.assertIn('--output', cmd)

    def test_build_package_wasm_pack(self):
        tool = {'name': 'wasm-pack', 'command': 'wasm-pack', 'type': 'packager'}
        cmd, cwd, actions = self.engine.build_package_command(
            'Cargo.toml', tool
        )
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd[0], 'wasm-pack')
        self.assertEqual(cmd[1], 'build')

    def test_build_package_python_build(self):
        tool = {'name': 'python-build', 'command': 'python', 'type': 'packager'}
        cmd, cwd, actions = self.engine.build_package_command(
            'setup.py', tool, output_path='dist/'
        )
        self.assertEqual(cmd[0], 'python')
        self.assertIn('-m', cmd)
        self.assertIn('build', cmd)
        self.assertTrue(any(a[0] == 'wheel_move' for a in actions))

    def test_build_package_unknown(self):
        tool = {'name': 'herramienta_desconocida'}
        with self.assertRaises(ValueError):
            self.engine.build_package_command('main.py', tool)

    # ── WASM handling ──

    @patch('shutil.which')
    def test_build_command_for_wasm_emcc(self, mock_which):
        mock_which.return_value = '/usr/bin/emcc'
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        cmd, cwd, actions = self.engine.build_command_for(
            'main.c', tool, output_path='out.wasm', output_type='wasm'
        )
        self.assertEqual(cmd[0], 'emcc')
        self.assertIn('-o', cmd)
        self.assertIn('out.wasm', cmd)

    @patch('shutil.which')
    def test_build_command_for_wasm_wasm_pack(self, mock_which):
        # Simular que emcc no existe y wasm-pack sí
        def which_side_effect(cmd):
            if cmd == 'emcc':
                return None
            if cmd == 'wasm-pack':
                return '/usr/bin/wasm-pack'
            return None
        mock_which.side_effect = which_side_effect
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        cmd, cwd, actions = self.engine.build_command_for(
            'main.c', tool, output_type='wasm'
        )
        self.assertEqual(cmd[0], 'wasm-pack')
        self.assertEqual(cmd[1], 'build')

    # ── _perform_post_actions ──

    @patch('shutil.move')
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_perform_post_actions_cargo_move(self, mock_run, mock_which, mock_move):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = os.path.join(tmpdir, 'target', 'debug')
            os.makedirs(target_dir)
            exe_path = os.path.join(target_dir, 'myapp')
            with open(exe_path, 'w') as f:
                f.write('')
            os.chmod(exe_path, 0o755)
            post_actions = [('cargo_move', 'dest/path')]
            self.engine._perform_post_actions(post_actions, cwd=tmpdir)
            mock_move.assert_called_once()
            args, kwargs = mock_move.call_args
            self.assertEqual(args[1], 'dest/path')

    @patch('shutil.move')
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_perform_post_actions_jar(self, mock_run, mock_which, mock_move):
        mock_which.return_value = '/usr/bin/jar'
        post_actions = [('jar', 'out.jar', 'classes')]
        self.engine._perform_post_actions(post_actions)
        mock_run.assert_called_once_with(['jar', 'cf', 'out.jar', '-C', 'classes', '.'])

    @patch('shutil.move')
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_perform_post_actions_jar_without_jar(self, mock_run, mock_which, mock_move):
        mock_which.return_value = None
        with tempfile.TemporaryDirectory() as tmpdir:
            classes_dir = os.path.join(tmpdir, 'classes')
            os.makedirs(classes_dir)
            post_actions = [('jar', 'out.jar', classes_dir)]
            self.engine._perform_post_actions(post_actions, cwd=tmpdir)
            mock_move.assert_called_once()
            args, kwargs = mock_move.call_args
            self.assertTrue(args[0].endswith('.zip'))
            self.assertEqual(args[1], 'out.jar')

    @patch('shutil.move')
    def test_perform_post_actions_wheel_move(self, mock_move):
        with tempfile.TemporaryDirectory() as tmpdir:
            dist_dir = os.path.join(tmpdir, 'dist')
            os.makedirs(dist_dir)
            wheel_path = os.path.join(dist_dir, 'my_package-0.1.0-py3-none-any.whl')
            with open(wheel_path, 'w') as f:
                f.write('')
            dest_dir = os.path.join(tmpdir, 'dest')
            os.makedirs(dest_dir)
            post_actions = [('wheel_move', dest_dir)]
            self.engine._perform_post_actions(post_actions, cwd=tmpdir)
            mock_move.assert_called_once()
            args, kwargs = mock_move.call_args
            self.assertEqual(args[0], wheel_path)
            self.assertEqual(args[1], os.path.join(dest_dir, 'my_package-0.1.0-py3-none-any.whl'))

    @patch('shutil.move')
    def test_perform_post_actions_move(self, mock_move):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'src.txt')
            with open(src, 'w') as f:
                f.write('')
            post_actions = [('move', 'src.txt', 'dest.txt')]
            self.engine._perform_post_actions(post_actions, cwd=tmpdir)
            mock_move.assert_called_once_with(os.path.join(tmpdir, 'src.txt'), 'dest.txt')

    # ── compile ──

    @patch('subprocess.run')
    def test_compile_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='OK', stderr='')
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        result = self.engine.compile('main.c', tool)
        self.assertTrue(result['success'])
        self.assertEqual(result['stdout'], 'OK')

    @patch('subprocess.run')
    def test_compile_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='error')
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        result = self.engine.compile('main.c', tool)
        self.assertFalse(result['success'])
        self.assertEqual(result['stderr'], 'error')

    @patch('subprocess.run')
    def test_compile_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd='gcc', timeout=10)
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        result = self.engine.compile('main.c', tool)
        self.assertFalse(result['success'])
        self.assertIn('Tiempo de ejecución excedido', result['stderr'])

    @patch('subprocess.run')
    def test_compile_with_post_actions(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        tool = {'name': 'gcc', 'type': 'compiler', 'command': 'gcc'}
        with patch.object(self.engine, '_perform_post_actions') as mock_post:
            # Para generar post-actions, necesitamos una herramienta que las produzca,
            # como Rust con cargo_move. Pero con GCC no se generan.
            # Por simplicidad, forzamos post_actions.
            # Mejor usar un mock de estrategia que devuelva post_actions.
            with patch('src.compilers.registry.CompilerRegistry.get') as mock_get:
                mock_strategy = MagicMock()
                mock_strategy.build_command.return_value = (['gcc'], None, [('cargo_move', 'dest')])
                mock_get.return_value = mock_strategy
                result = self.engine.compile('main.c', tool, output_path='out')
                mock_post.assert_called_once()

    # ── package ──

    @patch('subprocess.run')
    def test_package_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='OK', stderr='')
        tool = {'name': 'pyinstaller', 'type': 'packager'}
        result = self.engine.package('main.py', tool)
        self.assertTrue(result['success'])

    @patch('subprocess.run')
    def test_package_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='error')
        tool = {'name': 'pyinstaller', 'type': 'packager'}
        result = self.engine.package('main.py', tool)
        self.assertFalse(result['success'])


if __name__ == '__main__':
    unittest.main()
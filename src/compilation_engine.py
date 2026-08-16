# compilation_engine.py
import subprocess
import os
import queue
import platform
import shutil

from . import logger
from .compilers.registry import CompilerRegistry

log = logger.Logger()

# Configuración multiplataforma para ocultar ventanas
if platform.system() == 'Windows':
    CREATE_NO_WINDOW = 0x08000000
    STARTUP_INFO = subprocess.STARTUPINFO()
    STARTUP_INFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    STARTUP_INFO.wShowWindow = 0
else:
    CREATE_NO_WINDOW = 0
    STARTUP_INFO = None


class CompilationEngine:
    """Gestiona la ejecución de compiladores, intérpretes y empaquetadores."""

    def __init__(self):
        self.process = None
        self.output_queue = queue.Queue()

    def build_package_command(self, file_path, tool, output_path=None, extra_args=None, target = "native"):
        """Construye (cmd, cwd, post_actions) para empaquetar."""
        extra_args = extra_args or []
        name = (tool.get('name') or '').lower()

        # Delegar en estrategia de empaquetado si existe
        strategy = CompilerRegistry.get(name)
        if strategy and hasattr(strategy, 'build_package_command'):
            return strategy.build_package_command(file_path, output_path, extra_args, target)

        # Fallback: usar la estrategia de compilación con output_type='exe'
        if strategy:
            return strategy.build_command(file_path, output_path, extra_args, 'exe', False, target)

        # Si no hay estrategia, lanzar error (como original)
        raise ValueError(f"Herramienta de empaquetado no soportada: {tool.get('name')}")

    def build_command_for(self, file_path, tool, output_path=None, extra_args=None,
                          output_type='', release_mode=False, target = 'native'):
        """Construye (cmd, cwd, post_actions) según tool, file_path y output_type."""
        extra_args = extra_args or []

        # ============================================================
        # 1. PRIMERO: manejar WASM (exactamente como en el original)
        # ============================================================
        if output_type == 'wasm':
            if shutil.which('emcc'):
                log.debug("[CompilationEngine] Usando emcc para WASM")
                cmd = ['emcc', file_path, '-o', output_path or (os.path.splitext(file_path)[0] + '.wasm')]
                return cmd, None, []
            if shutil.which('wasm-pack'):
                log.debug("[CompilationEngine] Usando wasm-pack para WASM")
                cmd = ['wasm-pack', 'build']
                cwd = os.path.dirname(file_path) or None
                return cmd, cwd, []
            # Si no hay herramientas, caer al fallback

        # ============================================================
        # 2. OBTENER NOMBRE DE LA HERRAMIENTA
        # ============================================================
        name = (tool.get('name') or tool.get('command') or '').lower()

        # ============================================================
        # 3. DELEGAR EN ESTRATEGIA ESPECÍFICA SI EXISTE
        # ============================================================
        strategy = CompilerRegistry.get(name)
        if strategy:
            log.debug(f"[CompilationEngine] Usando estrategia para: {name}")
            return strategy.build_command(file_path, output_path, extra_args, output_type, release_mode, target)

        # ============================================================
        # 4. FALLBACK GENÉRICO (comportamiento original para compiladores/interpretes)
        # ============================================================
        log.debug(f"[CompilationEngine] Sin estrategia para '{name}', usando fallback original")
        return self._legacy_fallback(file_path, tool, output_path, extra_args, output_type, release_mode)

    def _legacy_fallback(self, file_path, tool, output_path=None, extra_args=None,
                         output_type='exe', release_mode=False):
        """
        Copia exacta del código original de build_command_for
        para el caso de "compiler" e "interpreter".
        """
        extra_args = extra_args or []
        cmd = None
        cwd = None
        post_actions = []
        out = output_path

        # Fallback for C/C++ and other compilers
        if tool.get('type') == 'compiler':
            log.debug("[CompilationEngine] Fallback para C/C++ y otros lenguajes compilados")
            cmd = [tool['command']]
            out = out or os.path.splitext(file_path)[0]
            if output_type in ('exe', 'bin', 'go-bin', 'rust-bin', 'cargo-release'):
                out = out + ('.exe' if os.name == 'nt' and not out.endswith('.exe') else '')
            elif output_type in ('dll', 'so', 'dylib'):
                ext = {'dll': '.dll', 'so': '.so', 'dylib': '.dylib'}[output_type]
                out = out + ext if not out.endswith(ext) else out
            elif output_type in ('obj', 'o'):
                out = out + ('.obj' if os.name == 'nt' else '.o')
            elif output_type == 'pyd':
                out = out + ('.pyd' if os.name == 'nt' else '.so')
            if output_type in ('dll', 'so', 'dylib', 'pyd'):
                cmd.append('-shared')
            if output_type in ('obj',):
                cmd.append('-c')
            cmd.extend([ out, '-o', file_path])
            if extra_args:
                cmd.extend(extra_args)
            return cmd, None, post_actions

        # Interpreter fallback
        if tool.get('type') == 'interpreter':
            log.debug("[CompilationEngine] Fallback para lenguajes interpretados")
            cmd = [tool['command'], file_path]
            if extra_args:
                cmd.extend(extra_args)
            return cmd, None, post_actions

        # Si no matcheó nada
        log.debug("[CompilationEngine] No ha matcheado con ningún lenguaje de la lista")
        return None, None, []

    def build_compile_command(self, file_path, tool, output_path=None, extra_args=None,
                              output_type='', release_mode=False, target = 'native'):
        """Alias para build_command_for."""
        return self.build_command_for(file_path, tool, output_path, extra_args, output_type, release_mode, target)

    def _run_subprocess(self, cmd, cwd=None, timeout=None):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=STARTUP_INFO,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, '', 'Tiempo de ejecución excedido.'
        except Exception as e:
            return -1, '', f'Error al ejecutar comando: {e}'

    def _perform_post_actions(self, post_actions, cwd=None):
        """Ejecuta acciones posteriores (idéntico a tu original)."""
        for action in post_actions:
            kind = action[0]
            try:
                if kind == 'cargo_move':
                    dest = action[1]
                    project_dir = cwd or '.'
                    candidates = []
                    for root, dirs, files in os.walk(os.path.join(project_dir, 'target')):
                        for f in files:
                            if os.access(os.path.join(root, f), os.X_OK):
                                candidates.append(os.path.join(root, f))
                    if candidates:
                        src = sorted(candidates, key=os.path.getmtime)[-1]
                        shutil.move(src, dest)
                elif kind == 'jar':
                    jar_path = action[1]
                    class_dir = action[2] or os.path.dirname(jar_path)
                    if shutil.which('jar'):
                        subprocess.run(['jar', 'cf', jar_path, '-C', class_dir, '.'])
                    else:
                        shutil.make_archive(os.path.splitext(jar_path)[0], 'zip', class_dir)
                        zipname = os.path.splitext(jar_path)[0] + '.zip'
                        if os.path.exists(zipname):
                            shutil.move(zipname, jar_path)
                elif kind == 'wheel_move':
                    dest = action[1]
                    dist_dir = os.path.join(cwd or '.', 'dist')
                    if os.path.isdir(dist_dir):
                        wheels = [f for f in os.listdir(dist_dir) if f.endswith('.whl')]
                        if wheels:
                            wheels.sort(key=lambda f: os.path.getmtime(os.path.join(dist_dir, f)), reverse=True)
                            src = os.path.join(dist_dir, wheels[0])
                            if os.path.isdir(dest):
                                shutil.move(src, os.path.join(dest, wheels[0]))
                            else:
                                shutil.move(src, dest)
                elif kind == 'move':
                    src = action[1]
                    dst = action[2]
                    if not os.path.isabs(src):
                        src = os.path.join(cwd or '.', src)
                    if os.path.exists(src):
                        shutil.move(src, dst)
            except Exception as e:
                log.error(f"Post action failed: {e}")

    def compile(self, file_path, tool, output_path=None, extra_args=None,
                output_type='', release_mode=False, target = 'native'):
        """Compila o interpreta un archivo usando la herramienta especificada."""
        cmd, cwd, post_actions = self.build_compile_command(
            file_path, tool, output_path, extra_args, output_type, release_mode, target
        )
        if not cmd:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'No se pudo construir el comando para esta combinación.',
                'returncode': -1,
                'output_file': None
            }

        timeout = 300
        if output_type in ('cargo-release', 'wasm', 'apk', 'jar', 'whl'):
            timeout = 600

        log.debug(f"Comando a utilizar: {' '.join(cmd)}")
        returncode, stdout, stderr = self._run_subprocess(cmd, cwd=cwd, timeout=timeout)

        if returncode == 0 and post_actions:
            self._perform_post_actions(post_actions, cwd)

        output_file = output_path
        if not output_file and post_actions:
            for a in post_actions:
                if a[0] == 'cargo_move':
                    output_file = a[1]
                elif a[0] == 'jar':
                    output_file = a[1]
                elif a[0] == 'wheel_move':
                    output_file = a[1]

        result = {
            'success': returncode == 0,
            'stdout': stdout,
            'stderr': stderr,
            'returncode': returncode,
            'output_file': output_file
        }
        return result

    def package(self, file_path, tool, output_path=None, extra_args=None, target="native"):
        """Empaqueta un script interpretado usando la herramienta especificada."""
        cmd, cwd, post_actions = self.build_package_command(file_path, tool, output_path, extra_args, target)
        if not cmd:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'No se pudo construir el comando para empaquetado.',
                'returncode': -1,
                'output_file': None
            }

        timeout = 600
        returncode, stdout, stderr = self._run_subprocess(cmd, cwd=cwd, timeout=timeout)

        if returncode == 0 and post_actions:
            self._perform_post_actions(post_actions, cwd=cwd)

        output_file = output_path
        if not output_file and post_actions:
            for a in post_actions:
                if a[0] == 'wheel_move':
                    output_file = a[1]

        result = {
            'success': returncode == 0,
            'stdout': stdout,
            'stderr': stderr,
            'returncode': returncode,
            'output_file': output_file
        }
        return result
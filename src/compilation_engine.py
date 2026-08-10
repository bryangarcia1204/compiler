# compilation_engine.py
import subprocess
import os
import queue
import platform
import shutil

import logger
from output_types import OUTPUT_TYPE_MAP

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

    def build_package_command(self, file_path, tool, output_path=None, extra_args=None):
        """Construye (cmd, cwd, post_actions) para empaquetar."""
        extra_args = extra_args or []
        name = (tool.get('name') or '').lower()
        cmd = None
        cwd = None
        post_actions = []

        if name in ('python', 'pyinstaller'):
            executable = 'python'
            log.debug("[CompilationEngine] El archivo usa: 'python'")
            if tool.get('command') == executable:
                cmd = [tool['command'], '-m', 'pyinstaller']
            else:
                cmd = [tool['command']]
            if output_path:
                base_dir = os.path.dirname(output_path)
                if base_dir:
                    cmd.extend(['--distpath', base_dir])
                if os.path.splitext(output_path)[1]:
                    output_name = os.path.splitext(os.path.basename(output_path))[0]
                    cmd.extend(['--name', output_name])
            cmd.extend(['--onefile', '--noconsole'])
            if extra_args:
                cmd.extend(extra_args)
            cmd.append(file_path)
            log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}")
            return cmd, None, []

        if name in ('node', 'pkg'):
            log.debug(f"[CompilationEngine] El archivo usa: 'pkg' o 'node'")
            cmd = ['pkg']
            if output_path:
                cmd.extend(['--output', output_path])
            if extra_args:
                cmd.extend(extra_args)
            cmd.append(file_path)
            log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}")
            return cmd, None, []

        if name in ('wasm-pack', 'wasm'):
            log.debug(f"[CompilationEngine] El archivo usa: 'wasm-pack' o 'wasm'")
            cmd = ['wasm-pack', 'build']
            cwd = os.path.dirname(file_path) or None
            log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, la direccion para cwd es: {cwd}")
            return cmd, cwd, []

        if name == 'python-build':
            log.debug(f"[CompilationEngine] El archivo usa: 'python-build'")
            cmd = ['python', '-m', 'build', '--wheel']
            if extra_args:
                cmd.extend(extra_args)
            cwd = os.path.dirname(file_path) or None
            if output_path:
                post_actions.append(('wheel_move', output_path))
            log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, la direccion para cwd es: {cwd}, post-accion: {post_actions}")
            return cmd, cwd, post_actions

        raise ValueError(f"Herramienta de empaquetado no soportada: {tool.get('name')}")

    def build_command_for(self, file_path, tool, output_path=None, extra_args=None, output_type='exe', release_mode=False):
        """Construye (cmd, cwd, post_actions) según tool, file_path y output_type."""
        extra_args = extra_args or []
        name = (tool.get('name') or tool.get('command') or '').lower()
        cmd = None
        cwd = None
        post_actions = []
        out = output_path

        # Rust / Cargo
        if name in ('cargo', 'rust'):
            log.debug(f"[CompilationEngine] El archivo usa: 'cargo' o 'rust'")
            if os.path.basename(file_path).lower() == 'cargo.toml' or os.path.isdir(os.path.join(os.path.dirname(file_path), 'src')):
                cmd = ['cargo', 'build']
                if release_mode:
                    cmd.append('--release')
                cwd = os.path.dirname(file_path) or None
                if output_path:
                    post_actions.append(('cargo_move', output_path))
                log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, direccion para cwd: {cwd}, post-accion: {post_actions}")
                return cmd, cwd, post_actions
            else:
                out = out or os.path.splitext(file_path)[0] + ('.exe' if os.name == 'nt' else '')
                cmd = ['rustc', file_path, '-o', out]
                log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, post-accion: {post_actions}")
                return cmd, None, post_actions

        # Go
        if name == 'go':
            log.debug(f"[CompilationEngine] El archivo usa: 'go'")
            out = out or os.path.splitext(file_path)[0]
            cmd = ['go', 'build', '-o', out, file_path]
            if release_mode:
                cmd.extend(['-ldflags', '-s -w'])
            log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, post-accion: {post_actions}")
            return cmd, None, post_actions

        # Java (javac -> optional jar)
        if name in ('java', 'javac'):
            log.debug(f"[CompilationEngine] El archivo usa: 'javac' de 'java'")
            cmd = ['javac', file_path]
            if output_path and output_path.endswith('.jar'):
                class_dir = os.path.dirname(file_path)
                post_actions.append(('jar', output_path, class_dir))
            log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, post-accion: {post_actions}")
            return cmd, None, post_actions

        # Dotnet / csc
        if name in ('dotnet', 'csc'):
            log.debug(f"[CompilationEngine] El archivo usa: 'dotnet' o 'csc'")
            if tool.get('command') == 'dotnet':
                cmd = ['dotnet', 'build']
                if release_mode:
                    cmd.extend(['-c', 'Release'])
                if output_path:
                    outdir = os.path.dirname(output_path)
                    if outdir:
                        cmd.extend(['-o', outdir])
                cwd = os.path.dirname(file_path) or None
                log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, la direccion para cwd es: {cwd}, post-accion: {post_actions}")
                return cmd, cwd, post_actions
            else:
                out = out or os.path.splitext(file_path)[0] + ('.exe' if os.name == 'nt' else '')
                cmd = ['csc', '-out:' + out, file_path]
                log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, post-accion: {post_actions}")
                return cmd, None, post_actions

        # WASM (emscripten / wasm-pack)
        if output_type == 'wasm':
            if shutil.which('emcc'):
                log.debug(f"[CompilationEngine] El archivo usa: 'emcc'")
                cmd = ['emcc', file_path, '-o', output_path or (os.path.splitext(file_path)[0] + '.wasm')]
                log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, post-accion: {post_actions}")
                return cmd, None, post_actions
            if shutil.which('wasm-pack'):
                log.debug(f"[CompilationEngine] El archivo usa: 'wasm-pack' para compilado")
                cmd = ['wasm-pack', 'build']
                cwd = os.path.dirname(file_path) or None
                log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, la direccion para cwd es: {cwd}, post-accion: {post_actions}")
                return cmd, cwd, post_actions

        # Fallback for C/C++ and other compilers
        if tool.get('type') == 'compiler':
            log.debug(f"[CompilationEngine] Fallback para C/C++ y otros lenguages compilados")
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
            cmd.extend(['-o', out, file_path])
            if extra_args:
                cmd.extend(extra_args)
            log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, post-accion: {post_actions}")
            return cmd, None, post_actions

        # Interpreter fallback
        if tool.get('type') == 'interpreter':
            log.debug(f"[CompilationEngine] Fallback para lenguajes interpretado")
            cmd = [tool['command'], file_path]
            if extra_args:
                cmd.extend(extra_args)
            log.debug(f"[CompilationEngine] Comando enviado a consola: {cmd}, post-accion: {post_actions}")
            return cmd, None, post_actions

        log.debug(f"[CompilationEngine] No ha matcheado con ningun lenguage de la lista esperé actualizaciones")
        return None, None, []

    def build_compile_command(self, file_path, tool, output_path=None, extra_args=None, output_type='exe', release_mode=False):
            """Construye (cmd, cwd, post_actions) para compilar/ejecutar."""
            return self.build_command_for(file_path, tool, output_path, extra_args, output_type, release_mode)

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
        """Ejecuta acciones posteriores como mover binarios o crear jars."""
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

    def compile(self, file_path, tool, output_path=None, extra_args=None, output_type='exe', release_mode=False):
        """Compila o interpreta un archivo usando la herramienta especificada."""
        cmd, cwd, post_actions = self.build_compile_command(file_path, tool, output_path, extra_args, output_type, release_mode)
        if not cmd:
            return {'success': False, 'stdout': '', 'stderr': 'No se pudo construir el comando para esta combinación.', 'returncode': -1, 'output_file': None}

        timeout = 300
        if output_type in ('cargo-release', 'wasm', 'apk', 'jar', 'whl'):
            timeout = 600
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

    def package(self, file_path, tool, output_path=None, extra_args=None):
        """Empaqueta un script interpretado usando la herramienta especificada."""
        cmd, cwd, post_actions = self.build_package_command(file_path, tool, output_path, extra_args)
        if not cmd:
            return {'success': False, 'stdout': '', 'stderr': 'No se pudo construir el comando para empaquetado.', 'returncode': -1, 'output_file': None}

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
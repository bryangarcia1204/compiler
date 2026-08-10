# compiler_detector.py
import os
import platform
import shutil
import subprocess
import threading
import logger

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


def _get_python_cmd():
    """Detecta el comando Python disponible (prioriza python3 en Linux/macOS)."""
    if shutil.which('python3'):
        return 'python3'
    elif shutil.which('python'):
        return 'python'
    return None


PYTHON_CMD = _get_python_cmd()
PYTHON_AVAILABLE = PYTHON_CMD is not None

# ------------------------------------------------------------
# Capacidades de salida por herramienta
# ------------------------------------------------------------
TOOL_OUTPUT_CAPABILITIES = {
    'gcc': ['exe', 'bin', 'dll', 'so', 'dylib', 'a', 'lib', 'obj', 'pyd', 'wasm'],
    'g++': ['exe', 'bin', 'dll', 'so', 'dylib', 'a', 'lib', 'obj', 'pyd', 'wasm'],
    'clang': ['exe', 'bin', 'dll', 'so', 'dylib', 'a', 'lib', 'obj', 'pyd', 'wasm'],
    'rustc': ['exe', 'bin', 'dll', 'so', 'dylib', 'a', 'lib', 'obj', 'wasm'],
    'cargo': ['cargo-release', 'exe', 'bin', 'dll', 'so', 'wasm'],
    'go': ['go-bin', 'exe', 'bin', 'dll', 'so'],
    'java': ['class', 'jar', 'jar-exec', 'war', 'ear', 'aar', 'apk'],
    'javac': ['class', 'jar', 'jar-exec', 'war', 'ear', 'aar', 'apk'],
    'dotnet': ['dotnet', 'exe', 'dll', 'nupkg'],
    'csc': ['dotnet', 'exe', 'dll', 'nupkg'],
    'pyinstaller': ['exe', 'bin'],
    'pkg': ['nodebin', 'exe'],
    'python-build': ['whl', 'sdist', 'egg'],
    'wasm-pack': ['wasm'],
    'emscripten': ['wasm'],
}


def _get_version(cmd, args, timeout=1):
    """Obtiene la versión de una herramienta de forma silenciosa."""
    try:
        result = subprocess.run(
            [cmd] + args,
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
            startupinfo=STARTUP_INFO,
            timeout=timeout,
            shell=False
        )
        out = (result.stdout or result.stderr).strip()
        return out.splitlines()[0] if out else ''
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return ''


class CompilerDetector:
    _cached_tools = None
    _cache_lock = threading.Lock()
    _detecting = False

    @staticmethod
    def get_all_tools(force_refresh=False):
        if CompilerDetector._detecting:
            for _ in range(20):
                if not CompilerDetector._detecting:
                    break
                threading.Event().wait(0.1)
            if CompilerDetector._cached_tools is not None:
                return CompilerDetector._cached_tools

        if not force_refresh and CompilerDetector._cached_tools is not None:
            return CompilerDetector._cached_tools

        with CompilerDetector._cache_lock:
            if not force_refresh and CompilerDetector._cached_tools is not None:
                return CompilerDetector._cached_tools

            CompilerDetector._detecting = True
            tools = []

            # 1. Módulo C++
            try:
                import cpp_module
                cpp_tools = cpp_module.detect_compilers()
                for tool in cpp_tools:
                    tools.append({
                        'name': tool.name,
                        'command': tool.command,
                        'version': tool.version,
                        'extensions': tool.extensions,
                        'type': tool.type
                    })
            except Exception as e:
                log.error(f"Error en módulo C++: {e}")

            # 2. PyInstaller
            if PYTHON_AVAILABLE:
                try:
                    result = subprocess.run(
                        [PYTHON_CMD, '-m', 'pyinstaller', '--version'],
                        capture_output=True, text=True,
                        creationflags=CREATE_NO_WINDOW, startupinfo=STARTUP_INFO, timeout=2
                    )
                    if result.returncode == 0:
                        version = (result.stdout or result.stderr).strip()
                        tools.append({'name': 'PyInstaller', 'command': PYTHON_CMD, 'version': version, 'extensions': ['.py'], 'type': 'packager'})
                except Exception as e:
                    log.error(f"Error en chequeo de pyinstaller: {e}")

            if shutil.which('pyinstaller'):
                version = _get_version('pyinstaller', ['--version'])
                if not any(t['name'] == 'PyInstaller' for t in tools):
                    tools.append({'name': 'PyInstaller', 'command': 'pyinstaller', 'version': version, 'extensions': ['.py'], 'type': 'packager'})

            # 3. pkg (Node)
            if shutil.which('pkg'):
                version = _get_version('pkg', ['--version'])
                tools.append({'name': 'pkg', 'command': 'pkg', 'version': version, 'extensions': ['.js'], 'type': 'packager'})

            # 4. python-build (wheel)
            if PYTHON_AVAILABLE:
                try:
                    result = subprocess.run(
                        [PYTHON_CMD, '-m', 'build', '--version'],
                        capture_output=True, text=True,
                        creationflags=CREATE_NO_WINDOW, startupinfo=STARTUP_INFO, timeout=2
                    )
                    if result.returncode == 0:
                        version = _get_version(PYTHON_CMD, ['-m', 'build', '--version'])
                        tools.append({'name': 'python-build', 'command': PYTHON_CMD, 'version': version, 'extensions': ['.py'], 'type': 'packager'})
                except Exception as e:
                    log.error(f"Error en chequeo de python-build: {e}")

            if shutil.which('build'):
                version = _get_version('build', ['--version'])
                if not any(t['name'] == 'python-build' for t in tools):
                    tools.append({'name': 'python-build', 'command': 'build', 'version': version, 'extensions': ['.py'], 'type': 'packager'})

            # 5. wasm-pack / emcc
            if shutil.which('wasm-pack'):
                version = _get_version('wasm-pack', ['--version'])
                tools.append({'name': 'wasm-pack', 'command': 'wasm-pack', 'version': version, 'extensions': ['.rs', '.wasm', '.c', '.cpp'], 'type': 'packager'})
            if shutil.which('emcc'):
                version = _get_version('emcc', ['--version'])
                tools.append({'name': 'Emscripten', 'command': 'emcc', 'version': version, 'extensions': ['.c', '.cpp', '.cxx'], 'type': 'compiler'})

            # 6. Maven / Gradle
            if shutil.which('mvn'):
                version = _get_version('mvn', ['-v'])
                tools.append({'name': 'Maven', 'command': 'mvn', 'version': version, 'extensions': ['.java', '.pom'], 'type': 'builder'})
            if shutil.which('gradle') or os.path.exists('./gradlew') or os.path.exists('gradlew.bat'):
                cmd = 'gradle' if shutil.which('gradle') else ('./gradlew' if os.path.exists('./gradlew') else 'gradlew.bat')
                version = _get_version(cmd, ['-v']) if shutil.which(cmd) else ''
                tools.append({'name': 'Gradle', 'command': cmd, 'version': version, 'extensions': ['.java', '.kt', '.gradle'], 'type': 'builder'})

            # 7. Android tools
            if shutil.which('adb') or shutil.which('sdkmanager'):
                tools.append({'name': 'Android SDK', 'command': 'adb', 'version': '', 'extensions': ['.java', '.kt', '.gradle'], 'type': 'builder'})

            # 8. Rust, Go, Java, Dotnet
            if shutil.which('cargo'):
                version = _get_version('cargo', ['--version'])
                tools.append({'name': 'Cargo', 'command': 'cargo', 'version': version, 'extensions': ['.rs'], 'type': 'compiler'})
            if shutil.which('rustc'):
                version = _get_version('rustc', ['--version'])
                tools.append({'name': 'Rustc', 'command': 'rustc', 'version': version, 'extensions': ['.rs'], 'type': 'compiler'})
            if shutil.which('go'):
                version = _get_version('go', ['version'])
                tools.append({'name': 'Go', 'command': 'go', 'version': version, 'extensions': ['.go'], 'type': 'compiler'})
            if shutil.which('javac'):
                version = _get_version('javac', ['-version'])
                tools.append({'name': 'Java', 'command': 'javac', 'version': version, 'extensions': ['.java'], 'type': 'compiler'})
            if shutil.which('dotnet'):
                version = _get_version('dotnet', ['--version'])
                tools.append({'name': 'Dotnet', 'command': 'dotnet', 'version': version, 'extensions': ['.cs'], 'type': 'compiler'})

            # 9. MSVC (Windows)
            if platform.system() == 'Windows':
                vc_paths = [
                    r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat',
                    r'C:\Program Files (x86)\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
                ]
                if any(os.path.exists(p) for p in vc_paths):
                    tools.append({'name': 'MSVC', 'command': 'cl', 'version': 'Visual Studio 2022', 'extensions': ['.c', '.cpp', '.cc', '.cxx'], 'type': 'compiler'})

            CompilerDetector._cached_tools = tools
            CompilerDetector._detecting = False
            return tools

    @staticmethod
    def get_tool_output_capabilities(tool):
        name = tool.get('name', '').lower()
        if name in TOOL_OUTPUT_CAPABILITIES:
            return TOOL_OUTPUT_CAPABILITIES[name]
        if tool.get('type') == 'compiler':
            return ['exe', 'bin', 'dll', 'so', 'dylib', 'a', 'lib', 'obj', 'pyd', 'wasm']
        elif tool.get('type') == 'packager':
            return ['exe', 'bin']
        return []

    @staticmethod
    def filter_tools_by_language(tools, extension, lang_type=None):
        filtered = []
        for tool in tools:
            if extension in tool.get('extensions', []):
                if lang_type is None or tool.get('type') == lang_type:
                    filtered.append(tool)
        return filtered

    @staticmethod
    def get_installation_suggestion(tool_name):
        """Devuelve un comando o URL para instalar la herramienta."""
        suggestions = {
            'PyInstaller': 'pip install pyinstaller',
            'python-build': 'pip install build',
            'pkg': 'npm install -g pkg',
            'wasm-pack': 'cargo install wasm-pack',
            'emscripten': 'emsdk install latest',
            'cargo': 'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh',
            'go': 'https://golang.org/dl/',
            'java': 'https://adoptium.net/',
            'dotnet': 'https://dotnet.microsoft.com/download',
            'maven': 'https://maven.apache.org/download.cgi',
            'gradle': 'https://gradle.org/install/',
            'MSVC': 'Instalar Visual Studio Build Tools desde https://visualstudio.microsoft.com/visual-cpp-build-tools/',
        }
        return suggestions.get(tool_name, f'Instalar {tool_name} según documentación oficial')
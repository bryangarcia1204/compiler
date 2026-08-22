# src/project_analyzer.py
"""
Analizador semántico avanzado de proyectos.
Escanea recursivamente todos los archivos, lee su contenido (texto) y deduce
el tipo de proyecto, dependencias, estructura y posibles acciones a realizar.
"""

import os
import re
import json
import ast
import hashlib
import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from collections import Counter, defaultdict

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from ..utils.ai_client import AIClient
from ..utils import logger

log = logger.Logger()

# ──────────────────────────────────────────────────────────────
# 1. CONSTANTES Y MAPAS
# ──────────────────────────────────────────────────────────────

# Mapas de extensiones a lenguajes (prioridad)
EXTENSION_MAP = {
    # Lenguajes compilados
    '.c': 'c', '.cpp': 'c++', '.cc': 'c++', '.cxx': 'c++',
    '.h': 'c', '.hpp': 'c++', '.hxx': 'c++',
    '.rs': 'rust', '.go': 'go', '.java': 'java',
    '.cs': 'csharp', '.fs': 'fsharp', '.vb': 'vbnet',
    '.swift': 'swift', '.kt': 'kotlin', '.scala': 'scala',
    '.dart': 'dart', '.zig': 'zig', '.nim': 'nim',
    '.odin': 'odin', '.v': 'vlang',
    '.ex': 'elixir', '.exs': 'elixir', '.erl': 'erlang',
    '.hs': 'haskell', '.lhs': 'haskell',
    '.clj': 'clojure', '.cljs': 'clojure',
    '.rkt': 'racket',
    '.ml': 'ocaml', '.mli': 'ocaml', '.cppo': 'ocaml',
    '.pm': 'perl', '.pl': 'perl',
    # Lenguajes interpretados
    '.py': 'python', '.pyw': 'python',
    '.rb': 'ruby',
    '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
    '.ts': 'typescript', '.tsx': 'typescript',
    '.jsx': 'javascript',
    '.php': 'php',
    '.lua': 'lua',
    '.r': 'r',
    '.m': 'matlab', '.mm': 'objective-c',
    '.sh': 'bash', '.bash': 'bash', '.zsh': 'zsh', '.fish': 'fish',
    '.ps1': 'powershell',
    '.bat': 'batch', '.cmd': 'batch',
    '.sql': 'sql',
    # Web
    '.html': 'html', '.htm': 'html',
    '.css': 'css', '.scss': 'scss', '.sass': 'sass', '.less': 'less',
    '.vue': 'vue', '.svelte': 'svelte',
    '.xml': 'xml', '.json': 'json',
    '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
    '.ini': 'ini', '.cfg': 'ini', '.conf': 'conf',
    '.dockerfile': 'dockerfile',
    '.makefile': 'makefile', '.mk': 'makefile',
    '.cmake': 'cmake',
}

# Lenguajes y sus archivos de configuración típicos
CONFIG_FILES = {
    'python': ['requirements.txt', 'pyproject.toml', 'setup.py', 'setup.cfg', 'tox.ini', '.pylintrc', '.flake8'],
    'rust': ['Cargo.toml', 'rust-toolchain.toml', '.cargo/config.toml'],
    'go': ['go.mod', 'go.sum', '.golangci.yml'],
    'java': ['pom.xml', 'build.gradle', 'settings.gradle', 'gradle.properties', 'gradlew', 'gradlew.bat'],
    'c': ['Makefile', 'CMakeLists.txt', 'configure'],
    'c++': ['Makefile', 'CMakeLists.txt', 'configure'],
    'javascript': ['package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', '.npmrc', '.eslintrc.js', '.prettierrc'],
    'typescript': ['package.json', 'tsconfig.json', '.eslintrc.js'],
    'php': ['composer.json', 'composer.lock', '.php-cs-fixer.php'],
    'ruby': ['Gemfile', 'Gemfile.lock', '.ruby-version', 'Rakefile'],
    'csharp': ['*.csproj', '*.sln', '*.fsproj', '*.vbproj', 'Directory.Build.props', 'appsettings.json'],
    'dart': ['pubspec.yaml', 'pubspec.lock'],
    'elixir': ['mix.exs', 'mix.lock'],
    'haskell': ['*.cabal', 'stack.yaml'],
    'kotlin': ['build.gradle.kts', 'settings.gradle.kts', 'gradle.properties'],
    'swift': ['Package.swift', '*.xcodeproj'],
}

# Lenguajes compilados a binarios nativos
COMPILED_TO_NATIVE = {'c', 'c++', 'rust', 'go', 'zig', 'nim', 'odin', 'vlang', 'd'}

# Lenguajes que compilan a bytecode (Java, C#, etc.)
COMPILED_TO_BYTECODE = {'java', 'csharp', 'kotlin', 'scala', 'fsharp', 'vbnet'}

# Lenguajes interpretados
INTERPRETED = {
    'python', 'javascript', 'typescript', 'php', 'ruby', 'perl', 'lua',
    'r', 'bash', 'powershell', 'elixir', 'erlang', 'haskell'
}

# Tipos de salida según lenguaje y contexto
OUTPUT_TYPES = {
    'python': {'library': 'whl', 'application': 'exe', 'extension': 'pyd'},
    'rust': {'library': 'rlib', 'application': 'exe', 'cdylib': 'so'},
    'go': {'library': 'go-bin', 'application': 'exe'},
    'c': {'library': 'a', 'application': 'exe', 'shared': 'so', 'dinamico':'dll'},
    'c++': {'library': 'a', 'application': 'exe', 'shared': 'so', 'dinamico':'dll'},
    'java': {'library': 'jar', 'application': 'jar'},
    'csharp': {'library': 'dll', 'application': 'exe'},
    'javascript': {'application': 'nodebin', 'library': 'nodepkg'},
    'typescript': {'application': 'nodebin', 'library': 'nodepkg'},
    'ruby': {'library': 'gem', 'application': 'exe'},
    'php': {'application': 'phar', 'library': 'phppkg'},
}

# Palabras clave para detectar intención (expandido)
INTENT_KEYWORDS = {
    'library': ['lib', 'library', 'module', 'package', 'api', 'sdk', 'export', 'public', 'utils', 'helpers', 'util', 'base'],
    'application': ['app', 'application', 'cli', 'command', 'tool', 'main', 'start', 'run', 'server', 'service'],
    'extension': ['extension', 'bindings', 'wrapper', 'native', 'c_extension', 'ffi', 'pyd', 'dll', 'so', 'abi', 'pybind'],
    'web': ['web', 'http', 'rest', 'api', 'server', 'frontend', 'backend', 'middleware', 'router', 'controller'],
    'cli': ['cli', 'command', 'option', 'argument', 'parse', 'argparse', 'click', 'commander'],
    'gui': ['gui', 'window', 'button', 'dialog', 'widget', 'qt', 'tkinter', 'wxpython', 'curses', 'pygame'],
    'data_science': ['pandas', 'numpy', 'scipy', 'matplotlib', 'jupyter', 'dataframe', 'analysis', 'model', 'train', 'predict', 'tensorflow', 'torch'],
    'testing': ['test', 'spec', 'assert', 'mock', 'fixture', 'pytest', 'unittest'],
    'binary': ['binary', 'executable', 'compile', 'build', 'link', 'obj', 'lib', 'dll', 'so', 'pyd'],
    'script': ['script', 'automation', 'batch', 'cron', 'schedule'],
}

# Mapeo de arquitecturas de build
BUILD_ARCHITECTURES = {
    'python_setuptools': {'config_files': ['setup.py'], 'build_cmd': 'python setup.py build_ext --inplace', 'outputs': ['pyd', 'so']},
    'python_setuptools_cython': {'config_files': ['setup.py'], 'build_cmd': 'python setup.py build_ext --inplace', 'outputs': ['pyd', 'so'], 'requires': ['cython']},
    'python_scikit_build': {'config_files': ['pyproject.toml'], 'build_cmd': 'python -m build --wheel', 'outputs': ['whl'], 'requires': ['scikit-build']},
    'python_maturin': {'config_files': ['pyproject.toml', 'Cargo.toml'], 'build_cmd': 'maturin build', 'outputs': ['whl', 'pyd', 'so'], 'requires': ['maturin']},
    'c_cmake': {'config_files': ['CMakeLists.txt'], 'build_cmd': 'cmake -B build && cmake --build build', 'outputs': ['exe', 'so', 'dll', 'a', 'lib']},
    'c_makefile': {'config_files': ['Makefile'], 'build_cmd': 'make', 'outputs': ['exe', 'so', 'dll', 'a', 'lib']},
    'cpp_cmake': {'config_files': ['CMakeLists.txt'], 'build_cmd': 'cmake -B build && cmake --build build', 'outputs': ['exe', 'so', 'dll', 'a', 'lib']},
    'cpp_makefile': {'config_files': ['Makefile'], 'build_cmd': 'make', 'outputs': ['exe', 'so', 'dll', 'a', 'lib']},
    'rust_cargo': {'config_files': ['Cargo.toml'], 'build_cmd': 'cargo build', 'outputs': ['exe', 'rlib', 'so']},
    'rust_cargo_release': {'config_files': ['Cargo.toml'], 'build_cmd': 'cargo build --release', 'outputs': ['exe', 'rlib', 'so']},
    'go_build': {'config_files': ['go.mod'], 'build_cmd': 'go build', 'outputs': ['exe', 'go-bin']},
    'java_maven': {'config_files': ['pom.xml'], 'build_cmd': 'mvn clean compile package', 'outputs': ['jar']},
    'java_gradle': {'config_files': ['build.gradle'], 'build_cmd': 'gradle build', 'outputs': ['jar']},
    'dotnet_build': {'config_files': ['*.csproj', '*.sln'], 'build_cmd': 'dotnet build', 'outputs': ['exe', 'dll']},
    'dotnet_publish': {'config_files': ['*.csproj', '*.sln'], 'build_cmd': 'dotnet publish -c Release', 'outputs': ['exe']},
    'node_npm': {'config_files': ['package.json'], 'build_cmd': 'npm install && npm run build', 'outputs': ['nodebin']},
    'php_composer': {'config_files': ['composer.json'], 'build_cmd': 'composer install', 'outputs': ['phar']},
    'ruby_gem': {'config_files': ['Gemfile'], 'build_cmd': 'bundle install', 'outputs': ['gem']},
    'elixir_mix': {'config_files': ['mix.exs'], 'build_cmd': 'mix compile', 'outputs': ['exe']},
}


# ──────────────────────────────────────────────────────────────
# 2. CLASE PRINCIPAL
# ──────────────────────────────────────────────────────────────

class ProjectAnalyzer:
    """
    Analizador semántico avanzado de proyectos.
    """

    def __init__(
        self,
        project_dir: str,
        use_ai: bool = False,
        provider: str = "plataformia",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_file_size: int = 1024 * 1024  # 1MB
    ):
        
        self.project_dir = Path(project_dir).resolve()
        self.use_ai = use_ai
        self.max_file_size = max_file_size
        self.ai_client = None
        self.provider = provider
        if use_ai:
            self.ai_client = AIClient(provider=provider, api_key=api_key, model=model)

        # Estructura de análisis
        self.file_entries = []
        self.summary = {
            'project_dir': str(self.project_dir),
            'languages': Counter(),
            'files': [],
            'config_files': [],
            'source_files': [],
            'binary_files': [],
            'total_files': 0,
            'total_size': 0,
            'directories': [],
            'dependencies': set(),
            'imports': defaultdict(set),
            'exports': defaultdict(set),
            'main_files': [],
            'project_type': 'unknown',
            'intent_confidence': 0.0,
            'suggested_actions': [],
            'suggested_config_files': [],
            'suggested_build_architecture': None,
            'evidence': [],
            'ai_suggestions': None,
            'score_breakdown': {},
            'main_language': 'unknown',
        }

        # Ignorar directorios
        self.ignore_dirs = {
            '.git', '__pycache__', 'node_modules', 'target', 'dist', 'build',
            'venv', '.env', '.venv', 'env', 'lib', 'lib64', 'bin', 'sbin',
            'include', 'share', '.idea', '.vscode', '.pytest_cache', '.mypy_cache',
            '.ruff_cache', '.tox', '.eggs', '*.egg-info', '.coverage', 'htmlcov'
        }

        self.ignore_files = {'.DS_Store', 'Thumbs.db'}

    # ──────────────────────────────────────────────────────────
    # 3. ESCANEO DE ARCHIVOS
    # ──────────────────────────────────────────────────────────

    def analyze(self, archivo=None) -> Dict[str, Any]:
        """
        Realiza el análisis completo del proyecto.
        """
        log.info(f"[ProjectAnalyzer] Analizando proyecto en: {self.project_dir}")
        from ..config.compilador_config import CompiladorConfig
        self.compilador = CompiladorConfig(str(self.project_dir), auto_create=True)

        # 1. Escanear archivos
        self._scan_files(archivo)

        # 2. Analizar contenido de archivos fuente
        self._analyze_sources()

        # 3. Detectar dependencias
        self._detect_dependencies()

        # 4. Detectar archivos principales
        self._detect_main_files()

        # 5. Clasificar tipo de proyecto
        self._classify_project_type()

        # 6. Detectar arquitectura de build
        self._detect_build_architecture()

        # 7. Generar sugerencias
        self._generate_suggestions()

        # 8. Detectar necesidades de build (plan)
        self._detect_build_needs()

        # 8. Usar IA si está disponible
        if self.use_ai and self.ai_client and self.ai_client.is_available():
            self._get_ai_suggestions()

        # ── 11. ACTUALIZAR .compilador con el análisis ──
        self._update_compilador()

        resumen = self.summary
        for dicc in resumen["files"]:
            if dicc.get('content'):
                dicc.pop('content')

        log.info(f"[ProjectAnalyzer] Análisis completado. Tipo: {self.summary['project_type']}, "
                 f"Lenguaje: {self.summary['main_language']}")

        return self.summary

    # project_analyzer.py - Añadir al final de analyze()

    def _update_compilador(self):
        """Actualiza el archivo .compilador con los datos del análisis."""
        if not hasattr(self, 'compilador'):
            return

        # Actualizar con los datos del análisis
        self.compilador.set('languages', list(self.summary['languages'].keys()))
        self.compilador.set('dependencies', list(self.summary['dependencies']))
        self.compilador.set('project.type', self.summary['project_type'])
        self.compilador.set('main_files', self.summary.get('main_files', []))
        self.compilador.set('evidence', self.summary.get('evidence', []))
        self.compilador.set('score_breakdown', self.summary.get('score_breakdown', {}))
        self.compilador.set('suggested_config_files', self.summary.get('suggested_config_files', []))
        self.compilador.set('suggested_build_architecture', self.summary.get('suggested_build_architecture', ''))

        # Si hay build_plan, actualizar los steps de los targets
        build_plan = self.summary.get('build_plan', [])
        if build_plan:
            targets = self.compilador.get('targets', [])
            if not targets:
                targets = [{
                    "name": "default",
                    "description": "Compilación por defecto",
                    "steps": []
                }]

            # Actualizar los steps del target por defecto
            default_target = self.compilador.get('build.default_target', 'default')
            for target in targets:
                if target.get('name') == default_target:
                    target['steps'] = [
                        {
                            "language": step.get('language'),
                            "command": step.get('build_command', 'auto'),
                            "depends_on": step.get('requires', [])
                        }
                        for step in build_plan
                    ]
                    break

            self.compilador.set('targets', targets)

        # Guardar herramientas detectadas
        self._save_tools_to_compilador()

        self.compilador.save()

    def _save_tools_to_compilador(self):
        """Guarda las herramientas detectadas en el .compilador."""
        from ..detector.compiler_detector import CompilerDetector
        tools = CompilerDetector.get_all_tools()
        tools_info = {
            tool.get('name'): {
                'command': tool.get('command'),
                'version': tool.get('version'),
                'type': tool.get('type'),
                'extensions': tool.get('extensions', [])
            }
            for tool in tools
        }
        self.compilador.set('tools', tools_info)
# ──────────────────────────────────────────────────────────────
# 3. ESCANEO DE ARCHIVOS (VERSIÓN CORREGIDA)
# ──────────────────────────────────────────────────────────────

    def _scan_files(self, archivo = None):
        """Escanea recursivamente todos los archivos del directorio."""
        if not archivo:
            for root, dirs, files in os.walk(self.project_dir):
                # Filtrar directorios ignorados
                dirs[:] = [d for d in dirs if d not in self.ignore_dirs]

                rel_root = os.path.relpath(root, self.project_dir)
                self.summary['directories'].append(rel_root if rel_root != '.' else '')

                for file in files:
                    # Ignorar archivos por patrón
                    if any(fnmatch.fnmatch(file, pattern) for pattern in self.ignore_files):
                        continue

                    file_path = os.path.join(root, file)
                    rel_path = os.path.join(rel_root, file) if rel_root != '.' else file
                    ext = os.path.splitext(file)[1].lower()

                    try:
                        size = os.path.getsize(file_path)
                    except OSError:
                        size = 0

                    entry = {
                        'path': file_path,
                        'rel_path': rel_path,
                        'name': file,
                        'ext': ext,
                        'size': size,
                        'is_binary': False,
                        'is_source': False,
                        'is_config': False,
                        'language': None,
                        'content': '',
                        'hash': None,
                        'shebang': None,
                    }

                    # ── DETERMINAR SI ES BINARIO ──
                    # Primero, extensiones claramente binarias
                    binary_exts = {
                        '.exe', '.dll', '.so', '.pyd', '.pyc', '.pyo', 
                        '.o', '.obj', '.a', '.lib', '.class', '.jar', '.war', '.ear',
                        '.zip', '.gz', '.rar', '.7z', '.tar', '.bz2',
                        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp', '.svg',
                        '.mp3', '.mp4', '.avi', '.mkv', '.wav', '.flac',
                        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                        '.iso', '.img', '.bin'
                    }

                    if ext in binary_exts:
                        entry['is_binary'] = True
                        self.summary['binary_files'].append(entry)
                    else:
                        # Extensiones de texto conocidas
                        text_exts = {
                            '.py', '.pyw', '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',
                            '.rs', '.go', '.java', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx',
                            '.php', '.rb', '.lua', '.r', '.m', '.mm', '.sh', '.bash', '.zsh',
                            '.ps1', '.bat', '.cmd', '.sql', '.html', '.htm', '.css', '.scss',
                            '.sass', '.less', '.vue', '.svelte', '.xml', '.json', '.yaml',
                            '.yml', '.toml', '.ini', '.cfg', '.conf', '.txt', '.md', '.rst',
                            '.cmake', '.makefile', '.mk', '.dockerfile', '.gitignore', 
                            '.env', '.flake8', '.pylintrc', '.editorconfig'
                        }

                        if ext in text_exts or ext == '' or file.startswith('.'):
                            # Es texto, leer contenido
                            entry['is_binary'] = False
                            if size < self.max_file_size:
                                try:
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        content = f.read()
                                        entry['content'] = content
                                        entry['hash'] = hashlib.md5(content.encode()).hexdigest()
                                        # Detectar shebang
                                        if content.startswith('#!'):
                                            shebang_line = content.splitlines()[0] if content else ''
                                            entry['shebang'] = shebang_line
                                except UnicodeDecodeError:
                                    # Intentar con latin-1
                                    try:
                                        with open(file_path, 'r', encoding='latin-1') as f:
                                            content = f.read()
                                            entry['content'] = content
                                            entry['hash'] = hashlib.md5(content.encode()).hexdigest()
                                    except Exception:
                                        entry['is_binary'] = True
                                except Exception:
                                    entry['is_binary'] = True
                        else:
                            # Por defecto, considerar binario
                            entry['is_binary'] = True
                            self.summary['binary_files'].append(entry)

                        # ── DETERMINAR SI ES FUENTE ──
                        # Solo si no es binario y tiene extensión de fuente
                        if not entry['is_binary'] and ext in EXTENSION_MAP:
                            entry['is_source'] = True
                            entry['language'] = EXTENSION_MAP[ext]
                            self.summary['source_files'].append(entry)
                            self.summary['languages'][entry['language']] += 1

                        # ── DETERMINAR SI ES CONFIGURACIÓN ──
                        if not entry['is_binary']:
                            for lang, configs in CONFIG_FILES.items():
                                for pattern in configs:
                                    if fnmatch.fnmatch(file, pattern) or file == pattern:
                                        entry['is_config'] = True
                                        self.summary['config_files'].append(entry)
                                        break

                    self.summary['files'].append(entry)
                    self.summary['total_files'] += 1
                    self.summary['total_size'] += size
        else:
            
            
            if any(fnmatch.fnmatch(archivo, pattern) for pattern in self.ignore_files):
                return

            rel_root = os.path.relpath(archivo)
            file_path = os.path.join(archivo)
            rel_path = os.path.join(rel_root, archivo) if rel_root != '.' else archivo
            ext = os.path.splitext(archivo)[1].lower()

            try:
                size = os.path.getsize(file_path)
            except OSError:
                size = 0

            entry = {
                'path': file_path,
                'rel_path': rel_path,
                'name': archivo,
                'ext': ext,
                'size': size,
                'is_binary': False,
                'is_source': False,
                'is_config': False,
                'language': None,
                'content': '',
                'hash': None,
                'shebang': None,
            }

            # ── DETERMINAR SI ES BINARIO ──
            # Primero, extensiones claramente binarias
            binary_exts = {
                '.exe', '.dll', '.so', '.pyd', '.pyc', '.pyo', 
                '.o', '.obj', '.a', '.lib', '.class', '.jar', '.war', '.ear',
                '.zip', '.gz', '.rar', '.7z', '.tar', '.bz2',
                '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp', '.svg',
                '.mp3', '.mp4', '.avi', '.mkv', '.wav', '.flac',
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.iso', '.img', '.bin'
            }

            if ext in binary_exts:
                entry['is_binary'] = True
                self.summary['binary_files'].append(entry)
            else:
                # Extensiones de texto conocidas
                text_exts = {
                    '.py', '.pyw', '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',
                    '.rs', '.go', '.java', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx',
                    '.php', '.rb', '.lua', '.r', '.m', '.mm', '.sh', '.bash', '.zsh',
                    '.ps1', '.bat', '.cmd', '.sql', '.html', '.htm', '.css', '.scss',
                    '.sass', '.less', '.vue', '.svelte', '.xml', '.json', '.yaml',
                    '.yml', '.toml', '.ini', '.cfg', '.conf', '.txt', '.md', '.rst',
                    '.cmake', '.makefile', '.mk', '.dockerfile', '.gitignore', 
                    '.env', '.flake8', '.pylintrc', '.editorconfig'
                }

                if ext in text_exts or ext == '' or archivo.startswith('.'):
                    # Es texto, leer contenido
                    entry['is_binary'] = False
                    if size < self.max_file_size:
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                entry['content'] = content
                                entry['hash'] = hashlib.md5(content.encode()).hexdigest()
                                # Detectar shebang
                                if content.startswith('#!'):
                                    shebang_line = content.splitlines()[0] if content else ''
                                    entry['shebang'] = shebang_line
                        except UnicodeDecodeError:
                            # Intentar con latin-1
                            try:
                                with open(file_path, 'r', encoding='latin-1') as f:
                                    content = f.read()
                                    entry['content'] = content
                                    entry['hash'] = hashlib.md5(content.encode()).hexdigest()
                            except Exception:
                                entry['is_binary'] = True
                        except Exception:
                            entry['is_binary'] = True
                else:
                    # Por defecto, considerar binario
                    entry['is_binary'] = True
                    self.summary['binary_files'].append(entry)

                # ── DETERMINAR SI ES FUENTE ──
                # Solo si no es binario y tiene extensión de fuente
                if not entry['is_binary'] and ext in EXTENSION_MAP:
                    entry['is_source'] = True
                    entry['language'] = EXTENSION_MAP[ext]
                    self.summary['source_files'].append(entry)
                    self.summary['languages'][entry['language']] += 1

                # ── DETERMINAR SI ES CONFIGURACIÓN ──
                if not entry['is_binary']:
                    for lang, configs in CONFIG_FILES.items():
                        for pattern in configs:
                            if fnmatch.fnmatch(file, pattern) or file == pattern:
                                entry['is_config'] = True
                                self.summary['config_files'].append(entry)
                                break

            self.summary['files'].append(entry)
            self.summary['total_files'] += 1
            self.summary['total_size'] += size

    def _is_binary_file(self, file_path: str) -> bool:
        """Detecta si un archivo es binario."""
        # Extensiones conocidas de binarios
        binary_exts = {
            '.exe', '.dll', '.so', '.pyd', '.pyc', '.pyo', '.o', '.obj',
            '.a', '.lib', '.class', '.jar', '.war', '.ear',
            '.zip', '.gz', '.rar', '.7z',
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp',
            '.mp3', '.mp4', '.avi', '.mkv',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
        }
        if os.path.splitext(file_path)[1].lower() in binary_exts:
            return True

        # Leer primeros 1024 bytes
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                if b'\0' in chunk:
                    return True
                # Si no es ASCII imprimible, es binario
                printable = all(c < 128 and (c == 9 or c == 10 or c == 13 or 32 <= c <= 126) for c in chunk)
                return not printable
        except Exception:
            return True

    # ──────────────────────────────────────────────────────────
    # 4. ANÁLISIS DE CONTENIDO
    # ──────────────────────────────────────────────────────────

    def _analyze_sources(self):
        """Analiza el contenido de los archivos fuente."""
        for entry in self.summary['source_files']:
            if entry['content']:
                self._analyze_file_content(entry)

    def _analyze_file_content(self, entry: Dict):
        """Analiza el contenido de un archivo individual."""
        content = entry['content']
        lang = entry['language']

        # Analizar según lenguaje
        analyzers = {
            'python': self._analyze_python_content,
            'javascript': self._analyze_js_content,
            'typescript': self._analyze_js_content,
            'rust': self._analyze_rust_content,
            'go': self._analyze_go_content,
            'java': self._analyze_java_content,
            'c': self._analyze_cpp_content,
            'c++': self._analyze_cpp_content,
            'php': self._analyze_php_content,
            'ruby': self._analyze_ruby_content,
            'elixir': self._analyze_elixir_content,
            'csharp': self._analyze_csharp_content,
            'swift': self._analyze_swift_content,
            'kotlin': self._analyze_kotlin_content,
            'bash': self._analyze_bash_content,
            'lua': self._analyze_lua_content,
        }

        if lang in analyzers:
            analyzers[lang](entry)

        # Detectar si es archivo principal
        if 'main' in entry['name'].lower() or self._has_main_entry(content, lang):
            if entry['path'] not in self.summary['main_files']:
                self.summary['main_files'].append(entry['path'])

    def _has_main_entry(self, content: str, lang: str) -> bool:
        """Detecta si un contenido tiene una función/entry point main."""
        patterns = {
            'python': r'(?:if\s+__name__\s*==\s*["\']__main__["\']|def\s+main\s*\()',
            'rust': r'fn\s+main\s*\(',
            'go': r'func\s+main\s*\(',
            'java': r'public\s+static\s+void\s+main\s*\(',
            'c': r'int\s+main\s*\(',
            'c++': r'int\s+main\s*\(',
            'javascript': r'(?:require\.main\s*===|module\.parent\s*===)',
            'php': r'#!/usr/bin/env\s+php',
            'ruby': r'#!/usr/bin/env\s+ruby',
            'elixir': r'def\s+main\s*\(',
            'csharp': r'static\s+void\s+Main\s*\(',
            'swift': r'@main\s+struct|UIApplicationMain',
            'kotlin': r'fun\s+main\s*\(',
        }
        if lang in patterns:
            return bool(re.search(patterns[lang], content))
        return False

    def _analyze_python_content(self, entry: Dict):
        """Analiza contenido de Python."""
        content = entry['content']
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.summary['imports']['python'].add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self.summary['imports']['python'].add(node.module.split('.')[0])
                # Detectar uso de pybind11
                if isinstance(node, ast.Name) and node.id == 'pybind11':
                    self.summary['imports']['python'].add('pybind11')
        except Exception:
            # Fallback: regex
            imports = re.findall(r'^(?:from|import)\s+([\w.]+)', content, re.MULTILINE)
            for imp in imports:
                self.summary['imports']['python'].add(imp.split('.')[0])

    def _analyze_js_content(self, entry: Dict):
        """Analiza contenido de JavaScript/TypeScript."""
        content = entry['content']
        # Require
        for match in re.findall(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content):
            if not match.startswith('.'):
                self.summary['imports']['javascript'].add(match.split('/')[0])
        # Import
        for match in re.findall(r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]", content):
            if not match.startswith('.'):
                self.summary['imports']['javascript'].add(match.split('/')[0])
        # ES6 import statements
        for match in re.findall(r"import\s+['\"]([^'\"]+)['\"]", content):
            if not match.startswith('.'):
                self.summary['imports']['javascript'].add(match.split('/')[0])

        if 'export' in content or 'import' in content:
            self.summary['evidence'].append(f"Archivo {entry['rel_path']} usa ES6 modules")

    def _analyze_rust_content(self, entry: Dict):
        """Analiza contenido de Rust."""
        content = entry['content']
        # Use statements
        for match in re.findall(r"use\s+([\w:]+);", content):
            dep = match.split('::')[0]
            if dep not in ['std', 'core', 'alloc', 'proc_macro']:
                self.summary['imports']['rust'].add(dep)
        # Extern crate
        for match in re.findall(r"extern\s+crate\s+([\w_]+);", content):
            self.summary['imports']['rust'].add(match)

    def _analyze_go_content(self, entry: Dict):
        """Analiza contenido de Go."""
        content = entry['content']
        # Single imports
        for match in re.findall(r'import\s+["\']([^"\']+)["\']', content):
            if not match.startswith('.'):
                self.summary['imports']['go'].add(match)
        # Import block
        for block in re.findall(r'import\s+\(([^)]*)\)', content, re.DOTALL):
            for line in re.findall(r'"([^"]+)"', block):
                if not line.startswith('.'):
                    self.summary['imports']['go'].add(line)

    def _analyze_java_content(self, entry: Dict):
        """Analiza contenido de Java."""
        content = entry['content']
        for match in re.findall(r'import\s+([\w.]+);', content):
            self.summary['imports']['java'].add(match)

    def _analyze_cpp_content(self, entry: Dict):
        """Analiza contenido de C/C++."""
        content = entry['content']
        if not content:
            return
            
        # Detectar includes
        import re
        include_matches = re.findall(r'#include\s+[<"]([^>"]+)[>"]', content)
        for inc in include_matches:
            self.summary['imports']['c++'].add(inc)
        
        # Detectar pybind11 (importante para extensiones Python)
        if 'pybind11' in content:
            self.summary['imports']['c++'].add('pybind11')
            self.summary['evidence'].append(f"Archivo {entry['rel_path']} usa pybind11")
        
        # Detectar función main
        if 'main(' in content and ('int main' in content or 'void main' in content):
            self.summary['main_files'].append(entry['path'])
            self.summary['evidence'].append(f"Archivo {entry['rel_path']} contiene función main")
        
        # Detectar si es una biblioteca (header-only o con clases)
        if 'class' in content or 'struct' in content:
            if 'pybind11' not in content:
                self.summary['evidence'].append(f"Archivo {entry['rel_path']} contiene definiciones de clase/struct")

    def _analyze_php_content(self, entry: Dict):
        """Analiza contenido de PHP."""
        content = entry['content']
        for match in re.findall(r'use\s+([\w\\\\]+);', content):
            self.summary['imports']['php'].add(match.split('\\')[0])
        for match in re.findall(r'(?:require|include)\s+[\'"]([^\'"]+)[\'"]', content):
            if not match.startswith('.'):
                self.summary['imports']['php'].add(match)

    def _analyze_ruby_content(self, entry: Dict):
        """Analiza contenido de Ruby."""
        content = entry['content']
        for match in re.findall(r'require\s+[\'"]([^\'"]+)[\'"]', content):
            self.summary['imports']['ruby'].add(match)
        for match in re.findall(r'gem\s+[\'"]([^\'"]+)[\'"]', content):
            self.summary['imports']['ruby'].add(match)

    def _analyze_elixir_content(self, entry: Dict):
        """Analiza contenido de Elixir."""
        content = entry['content']
        for match in re.findall(r'use\s+([\w.]+)', content):
            self.summary['imports']['elixir'].add(match)
        for match in re.findall(r'import\s+([\w.]+)', content):
            self.summary['imports']['elixir'].add(match)

    def _analyze_csharp_content(self, entry: Dict):
        """Analiza contenido de C#."""
        content = entry['content']
        for match in re.findall(r'using\s+([\w.]+);', content):
            self.summary['imports']['csharp'].add(match)

    def _analyze_swift_content(self, entry: Dict):
        """Analiza contenido de Swift."""
        content = entry['content']
        for match in re.findall(r'import\s+([\w.]+)', content):
            self.summary['imports']['swift'].add(match)

    def _analyze_kotlin_content(self, entry: Dict):
        """Analiza contenido de Kotlin."""
        content = entry['content']
        for match in re.findall(r'import\s+([\w.]+)', content):
            self.summary['imports']['kotlin'].add(match)

    def _analyze_bash_content(self, entry: Dict):
        """Analiza contenido de Bash."""
        content = entry['content']
        for match in re.findall(r'(?:source|\.)\s+([^\s]+)', content):
            self.summary['imports']['bash'].add(match)

    def _analyze_lua_content(self, entry: Dict):
        """Analiza contenido de Lua."""
        content = entry['content']
        for match in re.findall(r'require\s*\(\s*["\']([^"\']+)["\']\s*\)', content):
            self.summary['imports']['lua'].add(match)

    # ──────────────────────────────────────────────────────────
    # 5. DETECCIÓN DE DEPENDENCIAS
    # ──────────────────────────────────────────────────────────

    def _detect_dependencies(self):
        """Consolida todas las dependencias detectadas."""
        for lang, deps in self.summary['imports'].items():
            for dep in deps:
                if dep:  # Evitar vacíos
                    self.summary['dependencies'].add(dep)

        # Leer dependencias desde archivos de configuración
        for entry in self.summary['config_files']:
            content = entry.get('content', '')
            if not content:
                continue

            if entry['name'] == 'requirements.txt':
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        dep = re.split(r'[=<>\[;]', line)[0].strip()
                        if dep:
                            self.summary['dependencies'].add(dep)

            elif entry['name'] == 'pyproject.toml' and tomllib:
                try:
                    data = tomllib.loads(content)
                    deps = data.get('project', {}).get('dependencies', [])
                    for dep in deps:
                        if isinstance(dep, str):
                            clean = re.split(r'[=<>\[;]', dep)[0].strip()
                            if clean:
                                self.summary['dependencies'].add(clean)
                except Exception:
                    pass

            elif entry['name'] == 'package.json':
                try:
                    data = json.loads(content)
                    for dep in data.get('dependencies', {}).keys():
                        self.summary['dependencies'].add(dep)
                    for dep in data.get('devDependencies', {}).keys():
                        self.summary['dependencies'].add(dep)
                except Exception:
                    pass

            elif entry['name'] == 'Cargo.toml' and tomllib:
                try:
                    data = tomllib.loads(content)
                    for dep in data.get('dependencies', {}).keys():
                        self.summary['dependencies'].add(dep)
                except Exception:
                    pass

            elif entry['name'] == 'go.mod':
                for line in content.splitlines():
                    if line.strip().startswith('require'):
                        dep = re.findall(r'([\w./-]+)\s+', line)
                        if dep:
                            self.summary['dependencies'].add(dep[0])

            elif entry['name'] == 'composer.json':
                try:
                    data = json.loads(content)
                    for dep in data.get('require', {}).keys():
                        self.summary['dependencies'].add(dep)
                    for dep in data.get('require-dev', {}).keys():
                        self.summary['dependencies'].add(dep)
                except Exception:
                    pass

            elif entry['name'] == 'Gemfile':
                for line in content.splitlines():
                    match = re.match(r'gem\s+[\'"]([^\'"]+)[\'"]', line)
                    if match:
                        self.summary['dependencies'].add(match.group(1))

            elif entry['name'] == 'mix.exs':
                for match in re.findall(r'{:([\w_]+),', content):
                    self.summary['dependencies'].add(match)

            elif entry['name'] in ['pom.xml', 'build.gradle']:
                # Extraer groupId:artifactId
                for match in re.findall(r'<artifactId>([^<]+)</artifactId>', content):
                    self.summary['dependencies'].add(match)

    # ──────────────────────────────────────────────────────────
    # 6. DETECCIÓN DE ARCHIVOS PRINCIPALES
    # ──────────────────────────────────────────────────────────

    def _detect_main_files(self):
        """Detecta y consolida los archivos principales."""
        # Buscar archivos con función main en todos los lenguajes
        for entry in self.summary['source_files']:
            if entry.get('language') in ('c', 'c++', 'rust', 'go', 'java'):
                if 'main' in entry['content'].lower() if entry['content'] else False:
                    if entry['path'] not in self.summary['main_files']:
                        self.summary['main_files'].append(entry['path'])
        
        # Si no hay main_files, usar el primer archivo fuente que no sea binario
        if not self.summary['main_files'] and self.summary['source_files']:
            # Priorizar archivos con nombres comunes
            priority_names = ['main', 'app', 'program', 'index', 'run']
            for entry in self.summary['source_files']:
                name_lower = entry['name'].lower()
                for p in priority_names:
                    if p in name_lower:
                        self.summary['main_files'].append(entry['path'])
                        break
                if self.summary['main_files']:
                    break
            
            # Si aún no hay, usar el primer archivo
            if not self.summary['main_files']:
                self.summary['main_files'] = [self.summary['source_files'][0]['path']]

    # ──────────────────────────────────────────────────────────
    # 7. CLASIFICACIÓN DEL PROYECTO
    # ──────────────────────────────────────────────────────────

    def _classify_project_type(self):
        """Clasifica el tipo de proyecto basado en todos los datos recopilados."""
        scores = defaultdict(int)

        # 1. Basado en lenguaje principal
        if self.summary['languages']:
            main_lang = self.summary['languages'].most_common(1)[0][0]
            self.summary['main_language'] = main_lang

            # Python
            if main_lang == 'python':
                # Detectar extensión C++ (pybind11)
                has_cpp = any(e['language'] in ('c', 'cpp', 'c++') for e in self.summary['source_files'])
                if has_cpp and 'pybind11' in self.summary['dependencies']:
                    scores['extension'] += 4
                    scores['binary'] += 3
                elif has_cpp:
                    scores['extension'] += 2

                # Detectar librería
                config_names = [e['name'] for e in self.summary['config_files']]
                if 'setup.py' in config_names or 'pyproject.toml' in config_names:
                    scores['library'] += 3

                # Detectar aplicación CLI
                if any(dep in self.summary['dependencies'] for dep in ['click', 'argparse', 'typer']):
                    scores['cli'] += 2

                # Detectar web
                if any(dep in self.summary['dependencies'] for dep in ['flask', 'django', 'fastapi', 'aiohttp']):
                    scores['web'] += 2

                # Detectar GUI
                if any(dep in self.summary['dependencies'] for dep in ['tkinter', 'PyQt5', 'wxPython', 'PySide']):
                    scores['gui'] += 2

                # Detectar data science
                if any(dep in self.summary['dependencies'] for dep in ['numpy', 'pandas', 'scipy', 'matplotlib']):
                    scores['data_science'] += 2
                if 'tensorflow' in self.summary['dependencies'] or 'torch' in self.summary['dependencies']:
                    scores['data_science'] += 2

            # Rust
            elif main_lang == 'rust':
                if any('main.rs' in f['rel_path'] for f in self.summary['source_files']):
                    scores['application'] += 3
                else:
                    scores['library'] += 2
                # Detectar librería cdylib (para Python)
                if any('cdylib' in f['content'] for f in self.summary['config_files'] if f['name'] == 'Cargo.toml'):
                    scores['extension'] += 2

            # Go
            elif main_lang == 'go':
                if any('main.go' in f['rel_path'] for f in self.summary['source_files']):
                    scores['application'] += 3
                else:
                    scores['library'] += 2

            # C/C++
            elif main_lang in ('c', 'cpp', 'c++'):
                # Detectar extensión Python
                if 'pybind11' in self.summary['dependencies']:
                    scores['extension'] += 4
                    scores['binary'] += 3

                # Detectar shared library
                if any('SHARED' in f.get('content', '') for f in self.summary['config_files'] if f['name'] == 'CMakeLists.txt'):
                    scores['shared_library'] += 2

                # Detectar aplicación
                if any('main' in f['name'].lower() for f in self.summary['source_files']):
                    scores['application'] += 2

            # Java
            elif main_lang == 'java':
                if any('Main' in f['name'] for f in self.summary['source_files']):
                    scores['application'] += 2
                else:
                    scores['library'] += 2

            # JavaScript/TypeScript
            elif main_lang in ('javascript', 'typescript'):
                if 'package.json' in [e['name'] for e in self.summary['config_files']]:
                    # Detectar si es web
                    if any(dep in self.summary['dependencies'] for dep in ['react', 'vue', 'angular', 'express']):
                        scores['web'] += 2
                    if any(dep in self.summary['dependencies'] for dep in ['commander', 'yargs', 'chalk']):
                        scores['cli'] += 2

        # 2. Basado en evidencia textual
        for evidence in self.summary['evidence']:
            evidence_lower = evidence.lower()
            for intent, keywords in INTENT_KEYWORDS.items():
                for kw in keywords:
                    if kw in evidence_lower:
                        scores[intent] += 0.5

        # 3. Basado en dependencias
        for dep in self.summary['dependencies']:
            dep_lower = dep.lower()
            for intent, keywords in INTENT_KEYWORDS.items():
                for kw in keywords:
                    if kw in dep_lower:
                        scores[intent] += 0.3

        # 4. Seleccionar el tipo principal
        if scores:
            max_score = max(scores.values())
            best_types = [k for k, v in scores.items() if v == max_score]
            primary_type = best_types[0] if best_types else 'unknown'
            confidence = max_score / max(sum(scores.values()), 1)
            self.summary['project_type'] = primary_type
            self.summary['intent_confidence'] = confidence
            self.summary['score_breakdown'] = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5])
        else:
            self.summary['project_type'] = 'unknown'
            self.summary['intent_confidence'] = 0.3

    # ──────────────────────────────────────────────────────────
    # 8. DETECCIÓN DE ARQUITECTURA DE BUILD
    # ──────────────────────────────────────────────────────────

    def _detect_build_architecture(self):
        """Detecta la arquitectura de build más adecuada."""
        config_names = [e['name'] for e in self.summary['config_files']]
        main_lang = self.summary.get('main_language', 'unknown')
        deps = self.summary.get('dependencies', set())

        # Buscar en BUILD_ARCHITECTURES
        for arch, info in BUILD_ARCHITECTURES.items():
            configs_match = all(
                any(fnmatch.fnmatch(cfg, pattern) for cfg in config_names)
                for pattern in info['config_files']
            ) if info['config_files'] else False

            # Verificar dependencias requeridas
            requires_ok = True
            if info.get('requires'):
                for req in info['requires']:
                    if req not in deps:
                        requires_ok = False
                        break

            if configs_match and requires_ok:
                self.summary['suggested_build_architecture'] = arch
                return

        # Fallback por lenguaje
        lang_arch_map = {
            'python': 'python_setuptools',
            'rust': 'rust_cargo',
            'go': 'go_build',
            'c': 'c_makefile',
            'c++': 'cpp_makefile',
            'java': 'java_maven',
            'csharp': 'dotnet_build',
            'javascript': 'node_npm',
            'typescript': 'node_npm',
            'php': 'php_composer',
            'ruby': 'ruby_gem',
            'elixir': 'elixir_mix',
        }
        if main_lang in lang_arch_map:
            self.summary['suggested_build_architecture'] = lang_arch_map[main_lang]

    # ──────────────────────────────────────────────────────────
    # 9. GENERACIÓN DE SUGERENCIAS
    # ──────────────────────────────────────────────────────────

    def _generate_suggestions(self):
        """Genera sugerencias de archivos de configuración y acciones."""
        suggested_configs = []
        actions = []
        project_type = self.summary['project_type']
        main_lang = self.summary.get('main_language', 'unknown')
        config_names = [e['name'] for e in self.summary['config_files']]

        # Sugerir archivos según lenguaje y tipo
        lang_configs = {
            'python': ['requirements.txt', '.gitignore'],
            'rust': ['Cargo.toml', '.gitignore'],
            'go': ['go.mod', '.gitignore'],
            'c': ['Makefile', 'CMakeLists.txt', '.gitignore'],
            'c++': ['Makefile', 'CMakeLists.txt', '.gitignore'],
            'java': ['pom.xml', '.gitignore'],
            'javascript': ['package.json', '.gitignore'],
            'typescript': ['package.json', 'tsconfig.json', '.gitignore'],
            'php': ['composer.json', '.gitignore'],
            'ruby': ['Gemfile', '.gitignore'],
            'elixir': ['mix.exs', '.gitignore'],
            'csharp': ['*.csproj', '.gitignore'],
            'swift': ['Package.swift', '.gitignore'],
            'kotlin': ['build.gradle.kts', '.gitignore'],
        }

        for cfg in lang_configs.get(main_lang, []):
            if not any(fnmatch.fnmatch(name, cfg) for name in config_names):
                suggested_configs.append(cfg)

        # Sugerir acciones según tipo
        if project_type == 'extension':
            actions.append("Generar archivos de configuración para extensión nativa")
            actions.append("Compilar extensión: python setup.py build_ext --inplace")
        elif project_type == 'library':
            actions.append("Construir paquete: python -m build (u otro según lenguaje)")
            actions.append("Publicar en repositorio de paquetes")
        elif project_type == 'application':
            actions.append("Compilar y ejecutar la aplicación")
            actions.append("Crear ejecutable distribuible")
        elif project_type == 'web':
            actions.append("Instalar dependencias: npm install / pip install -r requirements.txt")
            actions.append("Iniciar servidor de desarrollo")
        elif project_type == 'cli':
            actions.append("Instalar como comando global")
            actions.append("Probar el comando localmente")

        self.summary['suggested_config_files'] = suggested_configs
        self.summary['suggested_actions'] = actions

    def _prepare_summary_for_ai(self, include_content: bool = False, max_content_size: int = 2000) -> Dict:
        """
        Prepara una copia del summary para enviar a la IA.
        - Si include_content es True, incluye el contenido de los archivos (limitado).
        - max_content_size: límite de caracteres por archivo.
        """
        import copy
        summary_copy = copy.deepcopy(self.summary)

        # Convertir sets a listas para JSON
        summary_copy['dependencies'] = list(summary_copy['dependencies'])
        summary_copy['imports'] = {k: list(v) for k, v in summary_copy['imports'].items()}
        summary_copy['exports'] = {k: list(v) for k, v in summary_copy['exports'].items()}
        summary_copy['languages'] = dict(summary_copy['languages'])

        # Manejar archivos
        for file_entry in summary_copy.get('files', []):
            if include_content and file_entry.get('content'):
                # Limitar tamaño del contenido
                content = file_entry['content']
                if len(content) > max_content_size:
                    file_entry['content'] = content[:max_content_size] + "\n... (truncado)"
            else:
                # Eliminar contenido para no sobrecargar
                file_entry.pop('content', None)

        return summary_copy
    # ──────────────────────────────────────────────────────────
    # 10. INTEGRACIÓN CON IA (ENRIQUECIDA)
    # ──────────────────────────────────────────────────────────

    def _get_ai_suggestions(self):
        """
        Usa IA para mejorar la detección y sugerencias.
        Envía TODO el summary a la IA.
        """
        if not self.ai_client or not self.ai_client.is_available():
            return

        # Preparar una copia del summary con contenido de archivos limitado
        summary_for_ai = self._prepare_summary_for_ai(include_content=True, max_content_size=2000)

        prompt = f"""
    Eres un analista de proyectos experto en compilación. Analiza TODOS los datos del siguiente resumen de proyecto y proporciona sugerencias para mejorar la compilación y estructura del proyecto.

    DATOS COMPLETOS DEL PROYECTO (en JSON):
    {json.dumps(summary_for_ai, indent=2, default=str)}

    Basándote en TODA esta información, responde SOLO con el siguiente JSON:
    {{
        "project_type": "tipo_principal",
        "project_subtype": "subtipo_especifico",
        "confidence": 0.85,
        "missing_configs": ["archivo1", "archivo2"],
        "build_commands": ["comando1", "comando2"],
        "recommendations": ["recomendación1", "recomendación2"],
        "binary_target": "pyd|so|dll|exe|jar|whl|ninguno"
    }}
    """

        try:
            kwargs = {}
            if self.provider == "deepseek":
                kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

            response = self.ai_client.chat(
                messages=[
                    {"role": "system", "content": "Eres un analista de proyectos experto en compilación. Responde SOLO con el JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
                **kwargs
            )

            if not response:
                log.warning("[ProjectAnalyzer] No se recibió respuesta de IA")
                return

            log.debug(f"[ProjectAnalyzer] Respuesta cruda de IA: {response[:300]}...")

            cleaned = self._extract_json_from_response(response)
            if not cleaned:
                log.warning("[ProjectAnalyzer] No se pudo extraer JSON de la respuesta")
                return

            data = json.loads(cleaned)

            # Guardar sugerencias
            self.summary['ai_suggestions'] = data

            # Mejorar clasificación si la IA da más confianza
            if data.get('confidence', 0) > self.summary.get('intent_confidence', 0):
                self.summary['project_type'] = data.get('project_type', self.summary['project_type'])
                self.summary['intent_confidence'] = data.get('confidence', self.summary['intent_confidence'])

            # Añadir configuraciones sugeridas
            for cfg in data.get('missing_configs', []):
                if cfg not in self.summary['suggested_config_files']:
                    self.summary['suggested_config_files'].append(cfg)

            if data.get('build_commands'):
                self.summary['ai_build_commands'] = data.get('build_commands')

            if data.get('recommendations'):
                self.summary['ai_recommendations'] = data.get('recommendations')

            if data.get('binary_target'):
                self.summary['binary_target'] = data.get('binary_target')

            log.info(f"[ProjectAnalyzer] Sugerencias de IA aplicadas: {data.get('project_type')} (confianza: {data.get('confidence', 0)})")

        except json.JSONDecodeError as e:
            log.warning(f"[ProjectAnalyzer] No se pudo parsear JSON de IA: {e}")
            log.debug(f"[ProjectAnalyzer] Respuesta que falló: {response[:300] if response else 'None'}")
        except Exception as e:
            log.error(f"[ProjectAnalyzer] Error en IA: {e}")

    # ──────────────────────────────────────────────────────────
    # 12. VEREDICTO CON IA (ENRIQUECIDO PARA TINYLLAMA)
    # ──────────────────────────────────────────────────────────

    def get_ai_veredict(self, custom_instructions: str = "") -> Optional[Dict]:
        """
        Obtiene un veredicto final de la IA sobre el proyecto.
        Enriquecido con información detallada para TinyLlama.
        """
        if not self.ai_client or not self.ai_client.is_available():
            log.warning("[ProjectAnalyzer] IA no disponible para veredicto")
            return None

        # ── 1. RECOPILAR INFORMACIÓN DETALLADA ──
        languages = dict(self.summary['languages'])
        project_type = self.summary['project_type']
        config_files = [e['name'] for e in self.summary['config_files']]
        deps = list(self.summary['dependencies'])[:10]
        main_files = [os.path.basename(f) for f in self.summary['main_files']]
        evidence = self.summary['evidence'][:5]
        score_breakdown = self.summary.get('score_breakdown', {})

        # Detectar si es extensión Python (pybind11)
        has_pybind11 = 'pybind11' in self.summary['dependencies']
        has_cpp = any(lang in ('c', 'c++', 'cpp') for lang in languages.keys())

        # Detectar archivos de prueba
        has_tests = any('test' in f['rel_path'].lower() for f in self.summary['source_files'])

        # ── 2. CONSTRUIR PROMPT ENRIQUECIDO ──
        prompt = f"""Eres un experto en análisis de proyectos. Estos son los datos con los q trabajas datos:

PROYECTO: {self.summary['project_dir']}
LENGUAJES DETECTADOS: {', '.join(languages.keys()) if languages else 'Desconocido'}
TIPO ACTUAL: {project_type}
CONFIANZA ACTUAL: {self.summary.get('intent_confidence', 0):.2f}

DEPENDENCIAS CLAVE:
{chr(10).join(f'  - {d}' for d in deps) if deps else '  - Ninguna'}

ARCHIVOS DE CONFIGURACIÓN:
{chr(10).join(f'  - {c}' for c in config_files) if config_files else '  - Ninguno'}

ARCHIVOS PRINCIPALES:
{chr(10).join(f'  - {f}' for f in main_files) if main_files else '  - Ninguno'}

EVIDENCIA:
{chr(10).join(f'  - {e}' for e in evidence) if evidence else '  - Ninguna'}

PUNTUACIÓN DE INTENCIONES:
{chr(10).join(f'  - {k}: {v:.2f}' for k, v in score_breakdown.items()) if score_breakdown else '  - No disponible'}

DATOS ADICIONALES:
- Tiene pybind11: {'Sí' if has_pybind11 else 'No'}
- Tiene C/C++: {'Sí' if has_cpp else 'No'}
- Tiene tests: {'Sí' if has_tests else 'No'}

Rectifica y mejora el análisis. {custom_instructions if custom_instructions else ''}

Da tu veredicto final en este formato exacto solo modifica los valores no las llaves:
{{
    "project_type": "extension",
    "main_language": "cpp",
    "intent_confidence": 0.85,
    "suggested_config_files": ["CMakeLists.txt", "Makefile"],
    "suggested_actions": ["Compilar con CMake", "Ejecutar pruebas"]
}}

SOLO EL JSON, sin explicaciones ni texto adicional.
"""

        try:
            # Usar temperatura baja para más precisión
            response = self.ai_client.chat(
                messages=[
                    {"role": "system", "content": "Eres un analista de proyectos que vas a dar tu "
                    "veredicto final segun los datos que se te den para finalizar la compilacion "
                    "de un proyecto. Responde SOLO con el JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            if not response:
                log.warning("[ProjectAnalyzer] No se recibió respuesta de IA")
                return None

            log.debug(f"[ProjectAnalyzer] Respuesta cruda de IA: {response}")

            # Limpiar y extraer JSON
            cleaned = self._extract_json_from_response(response)
            if not cleaned:
                log.warning("[ProjectAnalyzer] No se pudo extraer JSON de la respuesta")
                return None

            veredict = json.loads(cleaned)

            # Validar campos mínimos
            if 'project_type' in veredict:
                log.info(f"[ProjectAnalyzer] Veredicto obtenido: {veredict.get('project_type')} (confianza: {veredict.get('intent_confidence', 0)})")
                return veredict
            else:
                log.warning("[ProjectAnalyzer] Veredicto incompleto, falta project_type")
                return None

        except json.JSONDecodeError as e:
            log.error(f"[ProjectAnalyzer] Error parseando JSON: {e}")
            log.debug(f"[ProjectAnalyzer] Respuesta que falló: {response[:300] if response else 'None'}")
            return None
        except Exception as e:
            log.error(f"[ProjectAnalyzer] Error obteniendo veredicto: {e}")
            return None

    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """
        Extrae un objeto JSON de una respuesta de IA.
        Maneja respuestas que incluyen texto adicional.
        """
        import re

        if not response:
            return None

        # 1. Buscar JSON entre llaves (incluyendo anidado)
        json_pattern = r'\{[^{}]*\}(?:\s*\{[^{}]*\})*'
        matches = re.findall(json_pattern, response)

        for match in matches:
            try:
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue

        # 2. Buscar JSON entre ```json y ```
        json_block = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_block:
            try:
                content = json_block.group(1).strip()
                json.loads(content)
                return content
            except json.JSONDecodeError:
                pass

        # 3. Buscar JSON entre ``` y ```
        code_block = re.search(r'```\s*([\s\S]*?)\s*```', response)
        if code_block:
            try:
                content = code_block.group(1).strip()
                json.loads(content)
                return content
            except json.JSONDecodeError:
                pass

        # 4. Buscar cualquier cosa que parezca un objeto JSON con balance de llaves
        brace_count = 0
        start = -1
        for i, char in enumerate(response):
            if char == '{':
                if brace_count == 0:
                    start = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start != -1:
                    candidate = response[start:i+1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        continue

        # 5. Si no se encuentra JSON, buscar palabras clave y construir uno
        if 'project_type' in response.lower():
            log.warning("[ProjectAnalyzer] No se encontró JSON, construyendo desde la respuesta...")
            return self._build_json_from_text(response)

        return None

    def _build_json_from_text(self, text: str) -> Optional[str]:
        """
        Intenta construir un JSON a partir de texto cuando TinyLlama no devuelve JSON puro.
        """
        import re

        result = {}

        # Buscar patrones comunes
        patterns = {
            'project_type': r'project_type["\s:]+([a-zA-Z_]+)',
            'main_language': r'main_language["\s:]+([a-zA-Z_]+)',
            'intent_confidence': r'intent_confidence["\s:]+([0-9.]+)',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1)
                if key == 'intent_confidence':
                    try:
                        result[key] = float(value)
                    except Exception:
                        result[key] = 0.5
                else:
                    result[key] = value

        # Si no se encontró project_type, usar el que ya tenemos
        if 'project_type' not in result:
            result['project_type'] = self.summary.get('project_type', 'unknown')

        if 'main_language' not in result:
            result['main_language'] = self.summary.get('main_language', 'unknown')

        if 'intent_confidence' not in result:
            result['intent_confidence'] = self.summary.get('intent_confidence', 0.5)

        # Añadir campos adicionales por defecto
        result['suggested_config_files'] = self.summary.get('suggested_config_files', [])
        result['suggested_actions'] = self.summary.get('suggested_actions', [])

        return json.dumps(result, indent=2)

    def get_summary(self) -> str:
        """Devuelve un resumen legible del análisis."""
        result = self.summary
        evidence = result.get('evidence', [])[:5]
        lines = [
            "=" * 70,
            f"📁 Proyecto: {result.get('project_dir')}",
            f"📝 Lenguaje principal: {result.get('main_language', 'Desconocido')}",
            f"📄 Tipo: {result.get('project_type', 'Desconocido')}",
            f"🎯 Confianza: {result.get('intent_confidence', 0) * 100:.1f}%",
            f"📦 Total archivos: {result.get('total_files', 0)}",
            f"📂 Archivos fuente: {len(result.get('source_files', []))}",
            f"⚙️ Archivos de configuración: {len(result.get('config_files', []))}",
            f"📋 Archivos principales: {', '.join([os.path.basename(f) for f in result.get('main_files', [])[:3]])}",
            f"🔧 Arquitectura de build: {result.get('suggested_build_architecture', 'No detectada')}",
            f"🔍 **Evidencia:**\n {chr(10).join(['  • ' + e for e in evidence])}",
            "",
            "📦 Dependencias detectadas:",
        ]

        if result.get('dependencies'):
            for dep in list(result['dependencies'])[:10]:
                lines.append(f"  - {dep}")
            if len(result['dependencies']) > 10:
                lines.append(f"  ... y {len(result['dependencies']) - 10} más")
        else:
            lines.append("  (Ninguna detectada)")

        lines.append("")
        lines.append("📊 Puntuación de intenciones:")
        for intent, score in result.get('score_breakdown', {}).items():
            lines.append(f"  - {intent}: {score:.2f}")

        if result.get('suggested_config_files'):
            lines.append("")
            lines.append("💡 Archivos de configuración sugeridos:")
            for cfg in result['suggested_config_files']:
                lines.append(f"  - {cfg}")

        if result.get('suggested_actions'):
            lines.append("")
            lines.append("🚀 Acciones sugeridas:")
            for action in result['suggested_actions']:
                lines.append(f"  - {action}")

        if result.get('ai_suggestions'):
            lines.append("")
            lines.append("🤖 Sugerencias de IA:")
            ai = result['ai_suggestions']
            if ai.get('project_type'):
                lines.append(f"  - Tipo sugerido: {ai['project_type']}")
            if ai.get('build_commands'):
                lines.append(f"  - Comandos de build: {', '.join(ai['build_commands'][:2])}")
            if ai.get('recommendations'):
                for rec in ai.get('recommendations', [])[:3]:
                    lines.append(f"  - {rec}")

        lines.append("=" * 70)
        return "\n".join(lines)

    def _detect_cross_language_dependencies(self):
        """
        Detecta dependencias entre lenguajes de forma avanzada.
        
        Casos detectados:
        1. Python importa módulos C++ (nombres desde setup.py o archivos .cpp)
        2. Python y JS se comunican vía APIs HTTP/WebSocket
        3. JS ejecuta Python via child_process
        """
        dependencies = {
            'python_imports_cpp': [],      # (module_name, python_file, cpp_file)
            'js_python_http': [],          # (js_file, python_file, endpoint)
            'js_python_childprocess': [],  # (js_file, python_script)
            'python_js_http': [],          # (python_file, js_file, endpoint)
        }

        # ── 1. Detectar módulos C++ exportados ──
        cpp_modules = self._detect_cpp_modules()

        # ── 2. Buscar imports en Python ──
        for entry in self.summary['source_files']:
            if entry['language'] == 'python':
                content = entry.get('content', '')
                # Buscar imports de módulos que coincidan con cpp_modules
                import re
                imports = re.findall(r'^(?:from|import)\s+([\w.]+)', content, re.MULTILINE)
                for imp in imports:
                    module_name = imp.split('.')[0]
                    if module_name in cpp_modules:
                        dependencies['python_imports_cpp'].append({
                            'module': module_name,
                            'python_file': entry['rel_path'],
                            'cpp_file': cpp_modules[module_name]
                        })

                # ── 3. Detectar si Python expone una API HTTP ──
                if 'Flask' in content or 'FastAPI' in content or 'Django' in content:
                    endpoints = self._extract_http_endpoints(content)
                    if endpoints:
                        # Guardar para luego buscar coincidencias en JS
                        self.summary['python_http_endpoints'] = endpoints

                # ── 4. Detectar si Python usa child_process o subprocess ──
                if 'subprocess' in content or 'os.system' in content:
                    dependencies['python_executes_external'].append(entry['rel_path'])

        # ── 5. Detectar en JavaScript ──
        for entry in self.summary['source_files']:
            if entry['language'] in ('javascript', 'typescript'):
                content = entry.get('content', '')

                # ── 6. Detectar child_process en JS ──
                if 'child_process' in content or 'spawn' in content or 'exec' in content:
                    # Buscar qué archivo Python se ejecuta
                    matches = re.findall(r'["\'](.*\.py)["\']', content)
                    for py_file in matches:
                        dependencies['js_python_childprocess'].append({
                            'js_file': entry['rel_path'],
                            'python_script': py_file
                        })

                # ── 7. Detectar peticiones HTTP a endpoints Python ──
                if hasattr(self.summary, 'python_http_endpoints'):
                    for endpoint in self.summary['python_http_endpoints']:
                        if endpoint in content:
                            dependencies['js_python_http'].append({
                                'js_file': entry['rel_path'],
                                'python_file': self._find_python_file_for_endpoint(endpoint),
                                'endpoint': endpoint
                            })

        self.summary['cross_dependencies'] = dependencies

    def _detect_cpp_modules(self) -> Dict[str, str]:
        """
        Detecta módulos C++ que serán exportados a Python.
        Busca en setup.py, pyproject.toml y archivos .cpp con pybind11.
        """
        modules = {}

        # Buscar en setup.py
        for entry in self.summary['config_files']:
            if entry['name'] == 'setup.py':
                content = entry.get('content', '')
                # Buscar Extension(name=...)
                import re
                matches = re.findall(r"Extension\s*\(\s*['\"]([^'\"]+)['\"]", content)
                for match in matches:
                    module_name = match.split('.')[-1]
                    # Buscar el archivo .cpp asociado
                    cpp_file = self._find_cpp_file_for_module(module_name)
                    modules[module_name] = cpp_file

        # Buscar en pyproject.toml (con scikit-build)
        for entry in self.summary['config_files']:
            if entry['name'] == 'pyproject.toml':
                content = entry.get('content', '')
                # Buscar módulos definidos en [tool.setuptools.packages]
                import re
                matches = re.findall(r'packages\s*=\s*\[([^\]]*)\]', content)
                for match in matches:
                    pkgs = re.findall(r'["\']([^"\']+)["\']', match)
                    for pkg in pkgs:
                        # Buscar .cpp asociado
                        cpp_file = self._find_cpp_file_for_module(pkg)
                        modules[pkg] = cpp_file

        # Buscar en archivos .cpp con pybind11
        for entry in self.summary['source_files']:
            if entry['language'] in ('c', 'cpp', 'c++'):
                content = entry.get('content', '')
                if 'pybind11' in content:
                    # Buscar PYBIND11_MODULE(módulo, m)
                    import re
                    match = re.search(r'PYBIND11_MODULE\s*\(\s*([\w_]+)', content)
                    if match:
                        module_name = match.group(1)
                        modules[module_name] = entry['rel_path']

        return modules

    def _find_cpp_file_for_module(self, module_name: str) -> Optional[str]:
        """Busca un archivo .cpp que contenga el módulo."""
        for entry in self.summary['source_files']:
            if entry['language'] in ('c', 'cpp', 'c++'):
                if module_name in entry.get('rel_path', ''):
                    return entry['rel_path']
        return None

    def _extract_http_endpoints(self, content: str) -> List[str]:
        """Extrae endpoints HTTP de un archivo Python (Flask/FastAPI)."""
        endpoints = []
        import re

        # Flask
        matches = re.findall(r'@app\.route\s*\(\s*["\']([^"\']+)["\']', content)
        endpoints.extend(matches)

        # FastAPI
        matches = re.findall(r'@app\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', content)
        endpoints.extend(matches)

        # Django urls (simplificado)
        matches = re.findall(r"path\s*\(\s*['\"]([^'\"]+)['\"]", content)
        endpoints.extend(matches)

        return endpoints

    def _find_python_file_for_endpoint(self, endpoint: str) -> Optional[str]:
        """Busca qué archivo Python contiene un endpoint específico."""
        for entry in self.summary['source_files']:
            if entry['language'] == 'python':
                content = entry.get('content', '')
                if endpoint in content:
                    return entry['rel_path']
        return None

    def _detect_build_needs(self):
        """
        Detecta qué artefactos necesita y produce el proyecto.
        Usa las reglas de build para inferir el orden y las dependencias.
        """
        from ..builder.build_rules import BuildRules

        languages = list(self.summary['languages'].keys())
        rules = BuildRules.build_order(languages, self.summary)

        self.summary['build_order'] = rules
        self.summary['build_plan'] = []

        for rule_name in rules:
            rule = BuildRules.get_rule(rule_name)
            if rule:
                # Verificar si los archivos fuente coinciden con las extensiones de entrada
                has_inputs = False
                for f in self.summary['files']:
                    # Obtener el nombre del archivo (puede estar en 'path', 'rel_path' o 'name')
                    file_name = f.get('path') or f.get('rel_path') or f.get('name', '')
                    for ext in rule.input_extensions:
                        if file_name.endswith(ext):
                            has_inputs = True
                            break
                    if has_inputs:
                        break

                if has_inputs or rule.produces:
                    self.summary['build_plan'].append({
                        'name': rule.name,
                        'language': rule.language,
                        'description': rule.description,
                        'produces': [a.value for a in rule.produces],
                        'requires': [a.value for a in rule.requires],
                        'build_command': rule.build_command,
                    })
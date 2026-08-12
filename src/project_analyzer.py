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

from .ai_client import AIClient
from . import logger

log = logger.Logger()

# ──────────────────────────────────────────────────────────────
# 1. CONSTANTES Y MAPAS
# ──────────────────────────────────────────────────────────────

# Mapas de extensiones a lenguajes (prioridad)
EXTENSION_MAP = {
    # Lenguajes compilados
    '.c': 'c', '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
    '.h': 'c', '.hpp': 'cpp', '.hxx': 'cpp',
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
    'cpp': ['Makefile', 'CMakeLists.txt', 'configure'],
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
COMPILED_TO_NATIVE = {'c', 'cpp', 'rust', 'go', 'zig', 'nim', 'odin', 'vlang', 'd'}

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
    'c': {'library': 'a', 'application': 'exe', 'shared': 'so'},
    'cpp': {'library': 'a', 'application': 'exe', 'shared': 'so'},
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

        log.info(f"[ProjectAnalyzer] project_dir: {project_dir}, use_ai: {use_ai}, provider: {provider}, api_key: {api_key}, model: {model}, max_file_size: {max_file_size}")

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

    def analyze(self) -> Dict[str, Any]:
        """
        Realiza el análisis completo del proyecto.
        """
        log.info(f"[ProjectAnalyzer] Analizando proyecto en: {self.project_dir}")

        # 1. Escanear archivos
        self._scan_files()

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

        # 8. Usar IA si está disponible
        if self.use_ai and self.ai_client and self.ai_client.client:
            self._get_ai_suggestions()

        log.info(f"[ProjectAnalyzer] Análisis completado. Tipo: {self.summary['project_type']}, "
                 f"Lenguaje: {self.summary['main_language']}")
        log.debug(f"[ProjectAnalyzer] Resumen: {json.dumps(self.summary, default=str, indent=2)[:500]}...")

        return self.summary

# ──────────────────────────────────────────────────────────────
# 3. ESCANEO DE ARCHIVOS (VERSIÓN CORREGIDA)
# ──────────────────────────────────────────────────────────────

    def _scan_files(self):
        """Escanea recursivamente todos los archivos del directorio."""
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
            'cpp': self._analyze_cpp_content,
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
            'cpp': r'int\s+main\s*\(',
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
            self.summary['imports']['cpp'].add(inc)
        
        # Detectar pybind11 (importante para extensiones Python)
        if 'pybind11' in content:
            self.summary['imports']['cpp'].add('pybind11')
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
            if entry.get('language') in ('c', 'cpp', 'rust', 'go', 'java'):
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
                has_cpp = any(e['language'] in ('c', 'cpp') for e in self.summary['source_files'])
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
            elif main_lang in ('c', 'cpp'):
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
            'cpp': 'cpp_makefile',
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
        arch = self.summary.get('suggested_build_architecture')

        # Sugerir archivos según lenguaje y tipo
        lang_configs = {
            'python': ['requirements.txt', '.gitignore'],
            'rust': ['Cargo.toml', '.gitignore'],
            'go': ['go.mod', '.gitignore'],
            'c': ['Makefile', 'CMakeLists.txt', '.gitignore'],
            'cpp': ['Makefile', 'CMakeLists.txt', '.gitignore'],
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

    # ──────────────────────────────────────────────────────────
    # 10. INTEGRACIÓN CON IA
    # ──────────────────────────────────────────────────────────

    def _get_ai_suggestions(self):
        """Usa IA para mejorar la detección y sugerencias."""
        if not self.ai_client or not self.ai_client.client:
            return

        # Construir resumen para la IA
        summary_text = f"""
Proyecto: {self.project_dir}
Lenguaje principal: {self.summary.get('main_language', 'Desconocido')}
Tipo detectado: {self.summary.get('project_type', 'Desconocido')}
Confianza: {self.summary.get('intent_confidence', 0) * 100:.1f}%

Archivos fuente: {len([e for e in self.summary['source_files']])}
Archivos de configuración: {[e['name'] for e in self.summary['config_files']]}

Dependencias detectadas ({len(self.summary['dependencies'])}):
{', '.join(list(self.summary['dependencies'])[:15])}

Archivos principales: {[os.path.basename(f) for f in self.summary['main_files']]}

Puntuación de intenciones: {self.summary.get('score_breakdown', {})}

Evidencia recopilada:
{chr(10).join(['- ' + e for e in self.summary['evidence'][:5]])}

Arquitectura de build sugerida: {self.summary.get('suggested_build_architecture', 'No detectada')}
"""

        prompt = f"""
Analiza el siguiente proyecto de software y responde en formato JSON:

{summary_text}

Responde con este formato exacto:
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

        response = self.ai_client.chat([
            {"role": "system", "content": "Eres un experto en análisis de proyectos de software. Siempre respondes en formato JSON válido."},
            {"role": "user", "content": prompt}
        ], temperature=0.3, max_tokens=500, extra_body={"thinking": {"type": "enabled"}} if self.provider == "deepseek" else {})

        if response:
            try:
                data = json.loads(response)
                self.summary['ai_suggestions'] = data

                # Mejorar clasificación si la IA da más confianza
                if data.get('confidence', 0) > self.summary.get('intent_confidence', 0):
                    self.summary['project_type'] = data.get('project_type', self.summary['project_type'])
                    self.summary['intent_confidence'] = data.get('confidence', self.summary['intent_confidence'])

                # Añadir configuraciones sugeridas por IA
                for cfg in data.get('missing_configs', []):
                    if cfg not in self.summary['suggested_config_files']:
                        self.summary['suggested_config_files'].append(cfg)

                # Añadir comandos de build sugeridos por IA
                if data.get('build_commands'):
                    self.summary['ai_build_commands'] = data.get('build_commands')

                # Guardar recomendaciones
                if data.get('recommendations'):
                    self.summary['ai_recommendations'] = data.get('recommendations')

            except json.JSONDecodeError:
                log.warning("[ProjectAnalyzer] No se pudo parsear respuesta de IA")

    # ──────────────────────────────────────────────────────────
    # 11. OBTENER RESUMEN LEGIBLE
    # ──────────────────────────────────────────────────────────

    def get_summary(self) -> str:
        """Devuelve un resumen legible del análisis."""
        result = self.summary
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
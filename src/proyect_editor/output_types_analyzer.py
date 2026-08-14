# src/output_types_analyzer.py
"""
Mapa de tipos de salida para el analizador de proyectos.
"""

OUTPUT_TYPE_MAP_ANALIZER = {
    # Ejecutables
    '.exe': 'exe',
    '.bin': 'bin',
    '.app': 'app',

    # Bibliotecas dinámicas
    '.dll': 'dll',
    '.so': 'so',
    '.dylib': 'dylib',

    # Bibliotecas estáticas
    '.a': 'a',
    '.lib': 'lib',

    # Objetos
    '.o': 'o',
    '.obj': 'obj',

    # Python
    '.pyd': 'pyd',
    '.whl': 'whl',
    '.egg': 'egg',

    # Java
    '.jar': 'jar',
    '.class': 'class',
    '.war': 'war',
    '.ear': 'ear',

    # Web
    '.wasm': 'wasm',

    # Go
    '.go-bin': 'go-bin',

    # Rust
    '.rlib': 'rlib',
    '.rust-bin': 'rust-bin',

    # Node
    '.nodebin': 'nodebin',
    '.nodepkg': 'nodepkg',

    # .NET
    '.nupkg': 'nupkg',
}

# Inversión para búsqueda por extensión
EXTENSION_TO_OUTPUT_TYPE = {v: k for k, v in OUTPUT_TYPE_MAP_ANALIZER.items()}

# Extensiones de salida por tipo de proyecto
PROJECT_OUTPUT_EXTENSIONS = {
    'python': {
        'application': ['.exe', '.bin'],
        'library': ['.whl', '.egg'],
        'extension': ['.pyd', '.so'],
    },
    'rust': {
        'application': ['.exe', '.bin'],
        'library': ['.rlib'],
        'cdylib': ['.so'],
    },
    'go': {
        'application': ['.exe', '.bin'],
        'library': ['.go-bin'],
    },
    'c': {
        'application': ['.exe', '.bin'],
        'library': ['.a'],
        'shared': ['.so', '.dll'],
    },
    'cpp': {
        'application': ['.exe', '.bin'],
        'library': ['.a'],
        'shared': ['.so', '.dll'],
    },
    'java': {
        'application': ['.jar'],
        'library': ['.jar'],
    },
    'csharp': {
        'application': ['.exe'],
        'library': ['.dll'],
    },
    'javascript': {
        'application': ['.nodebin'],
        'library': ['.nodepkg'],
    },
    'typescript': {
        'application': ['.nodebin'],
        'library': ['.nodepkg'],
    },
}
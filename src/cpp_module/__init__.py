# cpp_module/__init__.py
"""
Módulo C++ para detección de compiladores.
"""

# Intentar importar el módulo compilado
try:
    import cpp_module
    from cpp_module import detect_compilers, CompilerInfo
except ImportError:
    # Si no está compilado, dar un mensaje útil
    raise ImportError(
        "El módulo C++ no está compilado. "
        "Ejecuta: python setup.py build_ext --inplace"
    )
__all__ = [
    'detect_compilers',
    'CompilerInfo',
    'cpp_module',
]
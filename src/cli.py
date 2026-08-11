#!/usr/bin/env python3
# src/cli.py
"""
Interfaz de línea de comandos para el Compilador/Empaquetador Profesional.
"""

import argparse
import sys
import os
from .compiler_detector import CompilerDetector
from .compilation_engine import CompilationEngine
from .output_types import OUTPUT_TYPE_MAP
from . import logger

log = logger.Logger()


def main():
    parser = argparse.ArgumentParser(
        description="Compilador/Empaquetador Profesional - CLI",
        epilog="Usa 'compilador-cli <comando> --help' para más información."
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Comando a ejecutar')

    # ── list-tools ──
    _parser_list = subparsers.add_parser('list-tools', help='Lista las herramientas detectadas en el sistema')

    # ── compile ──
    parser_compile = subparsers.add_parser('compile', help='Compila un archivo fuente')
    parser_compile.add_argument('file', help='Ruta del archivo fuente')
    parser_compile.add_argument('--tool', help='Nombre de la herramienta a usar (si no se especifica, se autodetecta)')
    parser_compile.add_argument('--output', '-o', help='Ruta de salida (opcional)')
    parser_compile.add_argument('--type', '-t', default='exe',
                                help='Tipo de salida (ej: exe, dll, obj, etc.)')
    parser_compile.add_argument('--release', '-r', action='store_true',
                                help='Modo release (optimizaciones)')
    parser_compile.add_argument('--args', '-a', help='Argumentos adicionales (entre comillas)')

    # ── package ──
    parser_package = subparsers.add_parser('package', help='Empaqueta un archivo (genera ejecutable independiente)')
    parser_package.add_argument('file', help='Ruta del archivo fuente')
    parser_package.add_argument('--tool', help='Nombre de la herramienta de empaquetado (si no se especifica, se autodetecta)')
    parser_package.add_argument('--output', '-o', help='Ruta de salida (opcional)')
    parser_package.add_argument('--args', '-a', help='Argumentos adicionales (entre comillas)')

    args = parser.parse_args()

    if args.command == 'list-tools':
        list_tools()
    elif args.command == 'compile':
        compile_file(args)
    elif args.command == 'package':
        package_file(args)


def list_tools():
    """Muestra todas las herramientas detectadas."""
    detector = CompilerDetector()
    tools = detector.get_all_tools()
    if not tools:
        print("No se detectaron herramientas.")
        return
    print(f"{'Nombre':<20} {'Versión':<25} {'Tipo':<12} {'Extensiones'}")
    print("-" * 80)
    for tool in tools:
        name = tool.get('name', '')
        version = (tool.get('version', '') or '')[:22]
        type_ = tool.get('type', '')
        exts = ', '.join(tool.get('extensions', []))
        print(f"{name:<20} {version:<25} {type_:<12} {exts}")


def compile_file(args):
    """Ejecuta la compilación de un archivo."""
    file_path = args.file
    if not os.path.isfile(file_path):
        print(f"Error: El archivo '{file_path}' no existe.", file=sys.stderr)
        sys.exit(1)

    detector = CompilerDetector()

    # 1. Seleccionar herramienta
    if args.tool:
        tool_name = args.tool
        tools = detector.get_all_tools()
        tool = next((t for t in tools if t.get('name', '').lower() == tool_name.lower()), None)
        if not tool:
            print(f"Error: Herramienta '{tool_name}' no encontrada.", file=sys.stderr)
            sys.exit(1)
    else:
        tool = detector.get_tool_for_file(file_path)
        if not tool:
            print(f"Error: No se pudo detectar una herramienta adecuada para '{file_path}'.", file=sys.stderr)
            sys.exit(1)
        print(f"Herramienta autodetectada: {tool.get('name')}")

    # 2. Preparar argumentos
    extra_args = args.args.split() if args.args else []
    output_type = args.type
    # Validar output_type (si es un nombre de display, convertirlo a código)
    if output_type in OUTPUT_TYPE_MAP.values():
        pass  # ya es código
    else:
        # Buscar el código correspondiente
        for display, code in OUTPUT_TYPE_MAP.items():
            if display.lower() == output_type.lower():
                output_type = code
                break
        else:
            print(f"Advertencia: Tipo de salida '{output_type}' no reconocido. Usando 'exe'.", file=sys.stderr)
            output_type = 'exe'

    # 3. Compilar
    engine = CompilationEngine()
    result = engine.compile(
        file_path=file_path,
        tool=tool,
        output_path=args.output,
        extra_args=extra_args,
        output_type=output_type,
        release_mode=args.release
    )

    # 4. Mostrar resultados
    if result['stdout']:
        print(result['stdout'])
    if result['stderr']:
        print(result['stderr'], file=sys.stderr)

    if result['success']:
        print(f"✅ Compilación exitosa. Salida: {result.get('output_file', 'N/A')}")
        sys.exit(0)
    else:
        print(f"❌ Compilación falló con código {result.get('returncode', -1)}.", file=sys.stderr)
        sys.exit(1)


def package_file(args):
    """Ejecuta el empaquetado de un archivo."""
    file_path = args.file
    if not os.path.isfile(file_path):
        print(f"Error: El archivo '{file_path}' no existe.", file=sys.stderr)
        sys.exit(1)

    detector = CompilerDetector()

    # 1. Seleccionar herramienta de empaquetado
    if args.tool:
        tool_name = args.tool
        tools = detector.get_all_tools()
        tool = next((t for t in tools if t.get('name', '').lower() == tool_name.lower()), None)
        if not tool:
            print(f"Error: Herramienta '{tool_name}' no encontrada.", file=sys.stderr)
            sys.exit(1)
    else:
        ext = os.path.splitext(file_path)[1].lower()
        tools = detector.get_all_tools()
        packagers = [t for t in tools if t.get('type') == 'packager' and ext in t.get('extensions', [])]
        if not packagers:
            print(f"Error: No se encontró un empaquetador para '{file_path}'.", file=sys.stderr)
            sys.exit(1)
        tool = packagers[0]
        print(f"Empaquetador autodetectado: {tool.get('name')}")

    # 2. Preparar argumentos
    extra_args = args.args.split() if args.args else []

    # 3. Empaquetar
    engine = CompilationEngine()
    result = engine.package(
        file_path=file_path,
        tool=tool,
        output_path=args.output,
        extra_args=extra_args
    )

    # 4. Mostrar resultados
    if result['stdout']:
        print(result['stdout'])
    if result['stderr']:
        print(result['stderr'], file=sys.stderr)

    if result['success']:
        print(f"✅ Empaquetado exitoso. Salida: {result.get('output_file', 'N/A')}")
        sys.exit(0)
    else:
        print(f"❌ Empaquetado falló con código {result.get('returncode', -1)}.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
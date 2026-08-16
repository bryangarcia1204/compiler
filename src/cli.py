#!/usr/bin/env python3
# src/cli.py
"""
Interfaz de línea de comandos para el Compilador/Empaquetador Profesional.
Soporta análisis de proyectos, generación de archivos de configuración y mejora con IA.
"""

import argparse
import sys
import os
import json
from .compiler_detector import CompilerDetector
from .compilation_engine import CompilationEngine
from .proyect_editor.project_analyzer import ProjectAnalyzer
from .proyect_editor.project_generator import ProjectGenerator
from .output_types import OUTPUT_TYPE_MAP
from . import logger
from .config_manager import load_config, save_config

log = logger.Logger()


def main():
    parser = argparse.ArgumentParser(
        description="Compilador/Empaquetador Profesional - CLI",
        epilog="Usa 'compilador-cli <comando> --help' para más información."
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Comando a ejecutar')

    # ── list-tools ──
    subparsers.add_parser('list-tools', help='Lista las herramientas detectadas en el sistema')

    # ── analyze ──
    parser_analyze = subparsers.add_parser('analyze', help='Analiza un proyecto y muestra un resumen')
    parser_analyze.add_argument('directory', help='Directorio del proyecto a analizar')
    parser_analyze.add_argument('--ai', action='store_true', help='Usar IA para mejorar el análisis')
    parser_analyze.add_argument('--provider', default='plataformia', help='Proveedor de IA (plataformia, deepseek, openai, groq, tinyllama)')
    parser_analyze.add_argument('--model', help='Modelo de IA a usar')
    parser_analyze.add_argument('--api-key', help='API Key para el proveedor de IA')
    parser_analyze.add_argument('--output', '-o', help='Guardar el análisis en un archivo JSON')

    # ── generate ──
    parser_generate = subparsers.add_parser('generate', help='Genera archivos de configuración para un proyecto')
    parser_generate.add_argument('directory', help='Directorio del proyecto')
    parser_generate.add_argument('--ai', action='store_true', help='Usar IA para generar archivos')
    parser_generate.add_argument('--provider', default='plataformia', help='Proveedor de IA')
    parser_generate.add_argument('--model', help='Modelo de IA')
    parser_generate.add_argument('--api-key', help='API Key para el proveedor')
    parser_generate.add_argument('--prompt', help='Prompt personalizado para la IA')

    # ── enhance ──
    parser_enhance = subparsers.add_parser('enhance', help='Mejora archivos de configuración con IA')
    parser_enhance.add_argument('directory', help='Directorio del proyecto')
    parser_enhance.add_argument('--ai', action='store_true', help='Usar IA para mejorar archivos')
    parser_enhance.add_argument('--provider', default='plataformia', help='Proveedor de IA')
    parser_enhance.add_argument('--model', help='Modelo de IA')
    parser_enhance.add_argument('--api-key', help='API Key para el proveedor')
    parser_enhance.add_argument('--prompt', help='Prompt personalizado para la IA')

    # ── compile ──
    parser_compile = subparsers.add_parser('compile', help='Compila un archivo fuente')
    parser_compile.add_argument('file', help='Ruta del archivo fuente')
    parser_compile.add_argument('--tool', help='Nombre de la herramienta a usar (si no se especifica, se autodetecta)')
    parser_compile.add_argument('--output', '-o', help='Ruta de salida (opcional)')
    parser_compile.add_argument('--type', '-t', default='exe',
                                help='Tipo de salida (ej: exe, dll, obj, etc.)')
    parser_compile.add_argument('--target', default='native',
                            help='Plataforma destino (ej: windows-x86_64, linux-arm64, wasm32)')
    parser_compile.add_argument('--release', '-r', action='store_true',
                                help='Modo release (optimizaciones)')
    parser_compile.add_argument('--args', '-a', help='Argumentos adicionales (entre comillas)')

    # ── package ──
    parser_package = subparsers.add_parser('package', help='Empaqueta un archivo (genera ejecutable independiente)')
    parser_package.add_argument('file', help='Ruta del archivo fuente')
    parser_package.add_argument('--tool', help='Nombre de la herramienta de empaquetado (si no se especifica, se autodetecta)')
    parser_package.add_argument('--output', '-o', help='Ruta de salida (opcional)')
    parser_package.add_argument('--args', '-a', help='Argumentos adicionales (entre comillas)')

    # ── build ──
    parser_build = subparsers.add_parser('build', help='Compila un proyecto multi-lenguaje')
    parser_build.add_argument('directory', help='Directorio del proyecto')
    parser_build.add_argument('--target', default='native', help='Target de compilación')

    args = parser.parse_args()

    if args.command == 'list-tools':
        list_tools()
    elif args.command == 'analyze':
        analyze_project(args)
    elif args.command == 'generate':
        generate_files(args)
    elif args.command == 'enhance':
        enhance_files(args)
    elif args.command == 'compile':
        compile_file(args)
    elif args.command == 'package':
        package_file(args)
    elif args.command == 'build':
        build_project(args)


# ──────────────────────────────────────────────────────────
# COMANDOS
# ──────────────────────────────────────────────────────────

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


def analyze_project(args):
    """Analiza un proyecto y muestra un resumen."""
    directory = args.directory
    if not os.path.isdir(directory):
        print(f"Error: El directorio '{directory}' no existe.", file=sys.stderr)
        sys.exit(1)

    print(f"Analizando proyecto en: {directory}")

    analyzer = ProjectAnalyzer(
        project_dir=directory,
        use_ai=args.ai,
        provider=args.provider,
        api_key=args.api_key,
        model=args.model
    )

    summary = analyzer.analyze()

    # Mostrar resumen
    print(analyzer.get_summary())

    # Guardar en JSON si se solicita
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"\n✅ Análisis guardado en: {args.output}")
        except Exception as e:
            print(f"Error guardando el análisis: {e}", file=sys.stderr)


def generate_files(args):
    """Genera archivos de configuración para un proyecto."""
    directory = args.directory
    if not os.path.isdir(directory):
        print(f"Error: El directorio '{directory}' no existe.", file=sys.stderr)
        sys.exit(1)

    print(f"Generando archivos para: {directory}")

    # Primero analizar el proyecto
    analyzer = ProjectAnalyzer(
        project_dir=directory,
        use_ai=args.ai,
        provider=args.provider,
        api_key=args.api_key,
        model=args.model
    )
    project_info = analyzer.analyze()

    # Generar archivos
    generator = ProjectGenerator(
        use_ai=args.ai,
        provider=args.provider,
        api_key=args.api_key,
        model=args.model
    )

    files = generator.generate_config_files(project_info, args.prompt or "")

    if not files:
        print("No se generaron archivos.")
        sys.exit(1)

    # Mostrar archivos generados y preguntar si guardar
    print(f"\n📁 Archivos generados ({len(files)}):")
    for name in files.keys():
        print(f"  - {name}")

    # Guardar automáticamente en el directorio del proyecto
    saved = 0
    for filename, content in files.items():
        filepath = os.path.join(directory, filename)
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            saved += 1
            print(f"✅ Guardado: {filepath}")
        except Exception as e:
            print(f"❌ Error guardando {filename}: {e}", file=sys.stderr)

    print(f"\n✅ {saved} archivos guardados en: {directory}")


def enhance_files(args):
    """Mejora archivos de configuración con IA."""
    directory = args.directory
    if not os.path.isdir(directory):
        print(f"Error: El directorio '{directory}' no existe.", file=sys.stderr)
        sys.exit(1)

    if not args.ai:
        print("Error: El comando 'enhance' requiere la bandera --ai", file=sys.stderr)
        sys.exit(1)

    print(f"Mejorando archivos para: {directory}")

    # Analizar proyecto
    analyzer = ProjectAnalyzer(
        project_dir=directory,
        use_ai=args.ai,
        provider=args.provider,
        api_key=args.api_key,
        model=args.model
    )
    project_info = analyzer.analyze()

    # Leer archivos de configuración existentes
    existing_files = {}
    config_files = project_info.get('config_files', [])
    for entry in config_files:
        if isinstance(entry, dict):
            name = entry.get('name')
            path = entry.get('path')
        else:
            name = os.path.basename(entry)
            path = entry
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    existing_files[name] = f.read()
            except Exception:
                pass

    if not existing_files:
        print("No se encontraron archivos de configuración para mejorar.", file=sys.stderr)
        sys.exit(1)

    # Mejorar archivos
    generator = ProjectGenerator(
        use_ai=args.ai,
        provider=args.provider,
        api_key=args.api_key,
        model=args.model
    )

    result = generator.enhance_files_with_ai(project_info, existing_files, args.prompt or "")

    files = result.get('files', {})
    build_cmd = result.get('build_command')

    if not files:
        print("No se mejoraron archivos.")
        sys.exit(1)

    # Mostrar archivos mejorados
    print(f"\n📁 Archivos mejorados ({len(files)}):")
    for name in files.keys():
        print(f"  - {name}")

    if build_cmd:
        print("\n🔧 Comando de build sugerido:")
        print(f"  {build_cmd.get('description', '')}")
        print(f"  Comando: {' '.join(build_cmd.get('cmd', []))}")

    # Guardar automáticamente
    saved = 0
    for filename, content in files.items():
        filepath = os.path.join(directory, filename)
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            saved += 1
            print(f"✅ Guardado: {filepath}")
        except Exception as e:
            print(f"❌ Error guardando {filename}: {e}", file=sys.stderr)

    print(f"\n✅ {saved} archivos mejorados guardados en: {directory}")


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

    # Validar output_type
    if output_type not in OUTPUT_TYPE_MAP.values():
        # Si no es un código, buscar por display_name
        found = False
        for display, code in OUTPUT_TYPE_MAP.items():
            if display.lower() == output_type:
                output_type = code
                found = True
                break
        if not found:
            print(f"Advertencia: Tipo de salida '{args.type}' no reconocido. Usando 'exe'.", file=sys.stderr)
            output_type = 'exe'

    # 3. Compilar
    engine = CompilationEngine()
    result = engine.compile(
        file_path=file_path,
        tool=tool,
        output_path=args.output,
        extra_args=extra_args,
        output_type=output_type,
        release_mode=args.release,
        target=args.target
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

    #Verificar si el target es nativo
    if args.target and args.target != 'native':
        # Detectar si es Python con PyInstaller
        if file_path.endswith('.py'):
            # Buscar PyOxidizer
            detector = CompilerDetector()
            tools = detector.get_all_tools()
            pyoxidizer = next((t for t in tools if t.get('name').lower() == 'PyOxidizer'.lower()), None)

            if pyoxidizer and tool.get('name') != 'PyOxidizer':
                print(f"🌍 Usando PyOxidizer para {args.target}.")
                tool = pyoxidizer
            elif not pyoxidizer:
                print(f"⚠️  PyInstaller no soporta cross-compilation a {args.target}. PyOxidizer no está instalado.", file=sys.stderr)
                print(f"⚠️  Continuando con plataforma nativa.", file=sys.stderr)
                args.target = 'native'

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
            print(f"Error: No se encontró un empaquetador para {file_path}.", file=sys.stderr)
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
        extra_args=extra_args,
        target=args.target
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

def build_project(args):
    """Compila un proyecto multi-lenguaje."""
    directory = args.directory
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' no existe.", file=sys.stderr)
        sys.exit(1)

    # Analizar proyecto
    from .proyect_editor.project_analyzer import ProjectAnalyzer
    analyzer = ProjectAnalyzer(directory, use_ai=False)
    project_info = analyzer.analyze()

    # Crear orquestador
    from .build_orchestrator import BuildOrchestrator
    orchestrator = BuildOrchestrator(directory)
    orchestrator.create_pipeline_from_rules(project_info)

    print("📦 Construyendo proyecto multi-lenguaje...")
    if orchestrator.run():
        print("✅ Construcción completada exitosamente.")
    else:
        print("❌ Construcción falló.", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
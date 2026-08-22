#!/usr/bin/env python3
# src/cli.py
"""
Interfaz de línea de comandos para el Compilador/Empaquetador Profesional.
Soporta análisis de proyectos, generación de archivos de configuración y mejora con IA.
"""

import argparse
import json
import os
import sys

import yaml

from ..config.compilador_config import CompiladorConfig
from ..detector.compiler_detector import CompilerDetector
from ..engine.compilation_engine import CompilationEngine
from ..plugins_market.plugin_loader import PluginLoader
from ..plugins_market.plugin_manager import PluginManager
from ..proyect_editor.project_analyzer import ProjectAnalyzer
from ..proyect_editor.project_generator import ProjectGenerator
from ..utils import logger
from ..utils.output_types import OUTPUT_TYPE_MAP

log = logger.Logger()


def main():
    parser = argparse.ArgumentParser(
        description="Compilador/Empaquetador Profesional - CLI",
        epilog="Usa 'compilador-cli <comando> --help' para más información.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Comando a ejecutar")

    # ── list-tools ──
    subparsers.add_parser("list-tools", help="Lista las herramientas detectadas en el sistema")

    # ── init ──
    parser_init = subparsers.add_parser("init", help="Inicializa un proyecto con .compilador")
    parser_init.add_argument("directory", nargs="?", default=".", help="Directorio del proyecto")

    # ── config ──
    parser_config = subparsers.add_parser(
        "config", help="Muestra o edita la configuración .compilador"
    )
    parser_config.add_argument("directory", help="Directorio del proyecto a analizar")
    parser_config.add_argument(
        "--show", "-sh", action="store_true", help="Muestra la configuración actual"
    )
    parser_config.add_argument(
        "--set", "-s", nargs=2, metavar=("KEY", "VALUE"), help="Establece un valor"
    )

    # ── analyze ──
    parser_analyze = subparsers.add_parser(
        "analyze", help="Analiza un proyecto y muestra un resumen"
    )
    parser_analyze.add_argument("directory", help="Directorio del proyecto a analizar")
    parser_analyze.add_argument(
        "--ai", action="store_true", help="Usar IA para mejorar el análisis"
    )
    parser_analyze.add_argument(
        "--provider",
        default="plataformia",
        help="Proveedor de IA (plataformia, deepseek, openai, groq, tinyllama)",
    )
    parser_analyze.add_argument("--model", help="Modelo de IA a usar")
    parser_analyze.add_argument("--api-key", help="API Key para el proveedor de IA")
    parser_analyze.add_argument("--output", "-o", help="Guardar el análisis en un archivo JSON")

    # ── generate ──
    parser_generate = subparsers.add_parser(
        "generate", help="Genera archivos de configuración para un proyecto"
    )
    parser_generate.add_argument("directory", help="Directorio del proyecto")
    parser_generate.add_argument("--ai", action="store_true", help="Usar IA para generar archivos")
    parser_generate.add_argument("--provider", default="plataformia", help="Proveedor de IA")
    parser_generate.add_argument("--model", help="Modelo de IA")
    parser_generate.add_argument("--api-key", help="API Key para el proveedor")
    parser_generate.add_argument("--prompt", help="Prompt personalizado para la IA")

    # ── enhance ──
    parser_enhance = subparsers.add_parser(
        "enhance", help="Mejora archivos de configuración con IA"
    )
    parser_enhance.add_argument("directory", help="Directorio del proyecto")
    parser_enhance.add_argument("--ai", action="store_true", help="Usar IA para mejorar archivos")
    parser_enhance.add_argument("--provider", default="plataformia", help="Proveedor de IA")
    parser_enhance.add_argument("--model", help="Modelo de IA")
    parser_enhance.add_argument("--api-key", help="API Key para el proveedor")
    parser_enhance.add_argument("--prompt", help="Prompt personalizado para la IA")

    # ── compile ──
    parser_compile = subparsers.add_parser("compile", help="Compila un archivo fuente")
    parser_compile.add_argument("file", help="Ruta del archivo fuente")
    parser_compile.add_argument(
        "--tool", help="Nombre de la herramienta a usar (si no se especifica, se autodetecta)"
    )
    parser_compile.add_argument("--output", "-o", help="Ruta de salida (opcional)")
    parser_compile.add_argument(
        "--type", "-t", default="exe", help="Tipo de salida (ej: exe, dll, obj, etc.)"
    )
    parser_compile.add_argument(
        "--target",
        default="native",
        help="Plataforma destino (ej: windows-x86_64, linux-arm64, wasm32)",
    )
    parser_compile.add_argument(
        "--release", "-r", action="store_true", help="Modo release (optimizaciones)"
    )
    parser_compile.add_argument("--args", "-a", help="Argumentos adicionales (entre comillas)")

    # ── package ──
    parser_package = subparsers.add_parser(
        "package", help="Empaqueta un archivo (genera ejecutable independiente)"
    )
    parser_package.add_argument("file", help="Ruta del archivo fuente")
    parser_package.add_argument(
        "--tool",
        help="Nombre de la herramienta de empaquetado (si no se especifica, se autodetecta)",
    )
    parser_package.add_argument("--output", "-o", help="Ruta de salida (opcional)")
    parser_package.add_argument("--args", "-a", help="Argumentos adicionales (entre comillas)")
    parser_package.add_argument(
        "--target",
        default="native",
        help="Plataforma destino (ej: windows-x86_64, linux-arm64, wasm32)",
    )

    # ── build ──
    parser_build = subparsers.add_parser("build", help="Compila un proyecto multi-lenguaje")
    parser_build.add_argument("directory", help="Directorio del proyecto")
    parser_build.add_argument("--target", default="native", help="Target de compilación")

    # ── plugin ──
    parser_plugin = subparsers.add_parser("plugin", help="Gestiona plugins del marketplace")
    plugin_subparsers = parser_plugin.add_subparsers(
        dest="plugin_action", required=True, help="Acción a realizar"
    )

    # plugin list
    plugin_subparsers.add_parser("list", help="Lista los plugins instalados")

    # plugin available
    plugin_subparsers.add_parser(
        "available", help="Lista los plugins disponibles en el marketplace"
    )

    # plugin loaded
    plugin_subparsers.add_parser("loaded", help="Lista los plugins cargados en memoria")

    # plugin install
    parser_install = plugin_subparsers.add_parser("install", help="Instala un plugin")
    parser_install.add_argument("plugin_id", help="ID del plugin a instalar")
    parser_install.add_argument("--version", help="Versión específica del plugin")

    # plugin uninstall
    parser_uninstall = plugin_subparsers.add_parser("uninstall", help="Desinstala un plugin")
    parser_uninstall.add_argument("plugin_id", help="ID del plugin a desinstalar")

    # plugin update
    parser_update = plugin_subparsers.add_parser("update", help="Actualiza un plugin")
    parser_update.add_argument("plugin_id", help="ID del plugin a actualizar")

    # plugin reload
    parser_reload = plugin_subparsers.add_parser(
        "reload", help="Recarga un plugin (útil para desarrollo)"
    )
    parser_reload.add_argument("plugin_id", help="ID del plugin a recargar")

    # plugin info
    parser_info = plugin_subparsers.add_parser("info", help="Muestra información de un plugin")
    parser_info.add_argument("plugin_id", help="ID del plugin")

    # plugin create
    parser_create = plugin_subparsers.add_parser(
        "create", help="Crea un nuevo plugin desde una plantilla"
    )
    parser_create.add_argument("name", help="Nombre del plugin")
    parser_create.add_argument(
        "--languages", "-l", help="Lenguajes soportados (separados por comas)", default=""
    )

    # ── enhance-config ──
    parser_enhance_config = subparsers.add_parser(
        "enhance-config", help="Mejora el archivo .compilador con IA"
    )
    parser_enhance_config.add_argument(
        "directory", nargs="?", default=".", help="Directorio del proyecto"
    )

    args = parser.parse_args()

    if args.command == "list-tools":
        list_tools()
    elif args.command == "init":
        init_project(args)
    elif args.command == "config":
        config_command(args)
    elif args.command == "analyze":
        analyze_project(args)
    elif args.command == "generate":
        generate_files(args)
    elif args.command == "enhance":
        enhance_files(args)
    elif args.command == "compile":
        compile_file(args)
    elif args.command == "package":
        package_file(args)
    elif args.command == "build":
        build_project(args)
    elif args.command == "enhance-config":
        enhance_config_command(args)
    elif args.command == "plugin":
        if args.plugin_action == "list":
            plugin_list()
        elif args.plugin_action == "available":
            plugin_available()
        elif args.plugin_action == "loaded":
            plugin_loaded()
        elif args.plugin_action == "install":
            plugin_install(args)
        elif args.plugin_action == "uninstall":
            plugin_uninstall(args)
        elif args.plugin_action == "update":
            plugin_update(args)
        elif args.plugin_action == "reload":
            plugin_reload(args)
        elif args.plugin_action == "info":
            plugin_info(args)
        elif args.plugin_action == "create":
            plugin_create(args)


# ── FUNCIONES DE PLUGINS ──


def plugin_list():
    """Lista los plugins instalados."""
    manager = PluginManager()

    plugins = manager.get_installed_plugins()

    if not plugins:
        print("No hay plugins instalados.")
        return

    print("\n📦 Plugins instalados:")
    print("-" * 70)

    # Plugins instalados
    for p in plugins:
        loaded = PluginLoader.is_loaded(p.id)
        status = "✅ Cargado" if loaded else "⏸️ Instalado"
        print(f"[CLI] {p.name} ({p.version}) - {status}")
        if p.description:
            print(f"[CLI] {p.description}")
    print("-" * 70)

    # Plugins cargados que no están en el registro
    loaded_ids = PluginLoader.get_loaded_ids()
    for pid in loaded_ids:
        if not any(p.id == pid for p in plugins):
            print(f"[CLI]  {pid} - ✅ Cargado automáticamente")
    print("-" * 70)


def plugin_available():
    """Lista los plugins disponibles en el marketplace."""
    manager = PluginManager()

    try:
        plugins = manager.get_available_plugins()
    except Exception as e:
        print(f"❌ Error cargando marketplace: {e}")
        return

    if not plugins:
        print("No hay plugins disponibles.")
        return

    print("\n📦 Plugins disponibles:")
    print("-" * 70)
    for p in plugins:
        name = p.get("name", p.get("id", "Unknown"))
        version = p.get("version", "latest")
        author = p.get("author", "Unknown")
        langs = ", ".join(p.get("supported_languages", []))
        desc = p.get("description", "")
        print(f"  {name} (v{version}) por {author}")
        if langs:
            print(f"    Lenguajes: {langs}")
        if desc:
            print(f"    {desc}")
        print()


def plugin_loaded():
    """Lista los plugins cargados en memoria."""
    loaded = PluginLoader.get_loaded_plugins()

    if not loaded:
        print("No hay plugins cargados en memoria.")
        return

    print("\n🔌 Plugins cargados en memoria:")
    print("-" * 50)
    for plugin_id, strategy_class in loaded.items():
        # Verificar si está instalado
        manager = PluginManager()
        installed = manager.registry.get_plugin(plugin_id)
        status = "✅ Instalado" if installed else "📦 Cargado desde archivo"
        print(f"  {plugin_id} -> {strategy_class.__name__} ({status})")
    print("-" * 50)


def plugin_install(args):
    """Instala un plugin."""
    manager = PluginManager()

    print(f"📥 Instalando plugin '{args.plugin_id}'...")

    if manager.install_plugin(args.plugin_id, args.version):
        # Cargar el plugin después de instalar
        if PluginLoader.load_plugin_by_id(args.plugin_id):
            print(f"✅ Plugin '{args.plugin_id}' instalado y cargado.")
        else:
            print(
                f"✅ Plugin '{args.plugin_id}' instalado, pero no se pudo cargar. Usa 'plugin reload {args.plugin_id}'."
            )
    else:
        print(f"❌ No se pudo instalar el plugin '{args.plugin_id}'.")


def plugin_uninstall(args):
    """Desinstala un plugin."""
    manager = PluginManager()

    print(f"🗑️ Desinstalando plugin '{args.plugin_id}'...")

    if manager.uninstall_plugin(args.plugin_id):
        print(f"✅ Plugin '{args.plugin_id}' desinstalado.")
    else:
        print(f"❌ No se pudo desinstalar el plugin '{args.plugin_id}'.")


def plugin_update(args):
    """Actualiza un plugin."""
    manager = PluginManager()

    print(f"🔄 Actualizando plugin '{args.plugin_id}'...")

    if manager.update_plugin(args.plugin_id):
        # Recargar después de actualizar
        PluginLoader.reload_plugin(args.plugin_id)
        print(f"✅ Plugin '{args.plugin_id}' actualizado y recargado.")
    else:
        print(f"❌ No se pudo actualizar el plugin '{args.plugin_id}'.")


def plugin_reload(args):
    """Recarga un plugin."""
    manager = PluginManager()

    print(f"🔄 Recargando plugin '{args.plugin_id}'...")

    if manager.reload_plugin(args.plugin_id):
        print(f"✅ Plugin '{args.plugin_id}' recargado correctamente.")
    else:
        print(f"❌ No se pudo recargar el plugin '{args.plugin_id}'.")


def plugin_info(args):
    """Muestra información de un plugin."""
    manager = PluginManager()

    # Verificar si está instalado
    installed = manager.registry.get_plugin(args.plugin_id)

    if installed:
        loaded = PluginLoader.is_loaded(args.plugin_id)
        print(f"\n📄 Información de '{installed.name}':")
        print(f"  ID: {installed.id}")
        print(f"  Versión: {installed.version}")
        print(f"  Autor: {installed.author}")
        print(f"  Descripción: {installed.description}")
        print(f"  Lenguajes: {', '.join(installed.supported_languages)}")
        print(f"  Dependencias: {', '.join(installed.dependencies) or 'Ninguna'}")
        print(f"  Estado: {'✅ Cargado' if loaded else '⏸️ Instalado'}")
        print(f"  Instalado: {installed.installed_at}")
        return

    # Si no está instalado, buscar en el marketplace
    try:
        available = manager.market.get_plugin_info(args.plugin_id)
        if available:
            print(f"\n📄 Información de '{available.get('name', args.plugin_id)}':")
            print(f"  ID: {args.plugin_id}")
            print(f"  Versión: {available.get('version', 'N/A')}")
            print(f"  Autor: {available.get('author', 'Unknown')}")
            print(f"  Descripción: {available.get('description', 'Sin descripción')}")
            print(f"  Lenguajes: {', '.join(available.get('supported_languages', []))}")
            print("  Estado: 📦 Disponible en el marketplace")
            return
    except Exception:
        pass

    print(f"❌ Plugin '{args.plugin_id}' no encontrado.")


def plugin_create(args):
    """Crea un nuevo plugin desde una plantilla."""
    from pathlib import Path

    name = args.name
    languages = [lang.strip() for lang in args.languages.split(",") if lang.strip()]

    if not languages:
        languages = ["custom"]

    # Generar plantilla
    template = PluginLoader.create_plugin_template(name, languages)

    # Guardar en el directorio de plugins
    plugins_dir = Path(__file__).parent / "compilers" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    filepath = plugins_dir / f"{name}.py"

    if filepath.exists():
        print(f"⚠️  El archivo {filepath} ya existe. ¿Sobrescribir?")
        response = input("Sobrescribir (s/N): ").strip().lower()
        if response != "s":
            print("Cancelado.")
            return

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"✅ Plugin '{name}' creado en {filepath}")

    # Preguntar si instalar
    response = input("¿Deseas instalar el plugin ahora? (s/N): ").strip().lower()
    if response == "s":
        manager = PluginManager()
        if manager.install_plugin(name):
            print(f"✅ Plugin '{name}' instalado y cargado.")
        else:
            print(f"❌ No se pudo instalar el plugin '{name}'.")


# ── COMANDOS DE PROYECTO ──


def init_project(args):
    """Inicializa un proyecto con .compilador"""
    config = CompiladorConfig(args.directory)
    if config.config_path.exists():
        print(f"⚠️  {config.config_path} ya existe.")
        config.load()
        print(f"✅ Proyecto inicializado en {args.directory}")
        return


def config_command(args):
    """Muestra o edita la configuración .compilador"""
    config = CompiladorConfig(args.directory if args.directory else ".")
    config.load()

    if args.show:
        print(yaml.dump(config.to_dict(), default_flow_style=False, indent=2))
        return

    if args.set:
        key, value = args.set
        try:
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif "." in value:
                value = float(value)
            else:
                value = int(value)
        except (ValueError, AttributeError):
            pass

        config.set(key, value)
        config.save()
        print(f"✅ {key} = {value}")
        return

    print("Uso: compilador-cli config --show  | --set KEY VALUE")


# ── FUNCIONES EXISTENTES (sin cambios) ──


def list_tools():
    detector = CompilerDetector()
    tools = detector.get_all_tools()
    if not tools:
        print("No se detectaron herramientas.")
        return
    print(f"{'Nombre':<20} {'Versión':<25} {'Tipo':<12} {'Extensiones'}")
    print("-" * 80)
    for tool in tools:
        name = tool.get("name", "")
        version = (tool.get("version", "") or "")[:22]
        type_ = tool.get("type", "")
        exts = ", ".join(tool.get("extensions", []))
        print(f"{name:<20} {version:<25} {type_:<12} {exts}")


def analyze_project(args):
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
        model=args.model,
    )

    summary = analyzer.analyze()
    print(analyzer.get_summary())

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"\n✅ Análisis guardado en: {args.output}")
        except Exception as e:
            print(f"Error guardando el análisis: {e}", file=sys.stderr)


def generate_files(args):
    directory = args.directory
    if not os.path.isdir(directory):
        print(f"Error: El directorio '{directory}' no existe.", file=sys.stderr)
        sys.exit(1)

    print(f"Generando archivos para: {directory}")

    analyzer = ProjectAnalyzer(
        project_dir=directory,
        use_ai=args.ai,
        provider=args.provider,
        api_key=args.api_key,
        model=args.model,
    )
    project_info = analyzer.analyze()

    generator = ProjectGenerator(
        use_ai=args.ai, provider=args.provider, api_key=args.api_key, model=args.model
    )

    files = generator.generate_config_files(project_info, args.prompt or "")

    if not files:
        print("No se generaron archivos.")
        sys.exit(1)

    print(f"\n📁 Archivos generados ({len(files)}):")
    for name in files.keys():
        print(f"  - {name}")

    saved = 0
    for filename, content in files.items():
        filepath = os.path.join(directory, filename)
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            saved += 1
            print(f"✅ Guardado: {filepath}")
        except Exception as e:
            print(f"❌ Error guardando {filename}: {e}", file=sys.stderr)

    print(f"\n✅ {saved} archivos guardados en: {directory}")


def enhance_files(args):
    directory = args.directory
    if not os.path.isdir(directory):
        print(f"Error: El directorio '{directory}' no existe.", file=sys.stderr)
        sys.exit(1)

    if not args.ai:
        print("Error: El comando 'enhance' requiere la bandera --ai", file=sys.stderr)
        sys.exit(1)

    print(f"Mejorando archivos para: {directory}")

    analyzer = ProjectAnalyzer(
        project_dir=directory,
        use_ai=args.ai,
        provider=args.provider,
        api_key=args.api_key,
        model=args.model,
    )
    project_info = analyzer.analyze()

    existing_files = {}
    config_files = project_info.get("config_files", [])
    for entry in config_files:
        if isinstance(entry, dict):
            name = entry.get("name")
            path = entry.get("path")
        else:
            name = os.path.basename(entry)
            path = entry
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing_files[name] = f.read()
            except Exception:
                pass

    if not existing_files:
        print("No se encontraron archivos de configuración para mejorar.", file=sys.stderr)
        sys.exit(1)

    generator = ProjectGenerator(
        use_ai=args.ai, provider=args.provider, api_key=args.api_key, model=args.model
    )

    result = generator.enhance_files_with_ai(project_info, existing_files, args.prompt or "")
    files = result.get("files", {})
    build_cmd = result.get("build_command")

    if not files:
        print("No se mejoraron archivos.")
        sys.exit(1)

    print(f"\n📁 Archivos mejorados ({len(files)}):")
    for name in files.keys():
        print(f"  - {name}")

    if build_cmd:
        print("\n🔧 Comando de build sugerido:")
        print(f"  {build_cmd.get('description', '')}")
        print(f"  Comando: {' '.join(build_cmd.get('cmd', []))}")

    saved = 0
    for filename, content in files.items():
        filepath = os.path.join(directory, filename)
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            saved += 1
            print(f"✅ Guardado: {filepath}")
        except Exception as e:
            print(f"❌ Error guardando {filename}: {e}", file=sys.stderr)

    print(f"\n✅ {saved} archivos mejorados guardados en: {directory}")


def compile_file(args):
    """Ejecuta la compilación de un archivo usando .compilador si existe"""
    file_path = args.file
    if not os.path.isfile(file_path):
        print(f"Error: El archivo '{file_path}' no existe.", file=sys.stderr)
        sys.exit(1)

    detector = CompilerDetector()

    # ── CARGAR .compilador ──
    project_dir = os.path.dirname(file_path)
    config = CompiladorConfig(project_dir, auto_create=True)

    # ── DETECTAR LENGUAJE ──
    ext = os.path.splitext(file_path)[1].lower()
    lang_map = {
        ".c": "c",
        ".cpp": "cpp",
        ".py": "python",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".js": "javascript",
        ".ts": "typescript",
    }
    language = lang_map.get(ext, "unknown")

    # ── SI .compilador TIENE COMANDO DEFINIDO PARA EL LENGUAJE ──
    if language != "unknown":
        cmd_from_config = config.get_build_command_for_language(language)
        if cmd_from_config:
            print(f"📄 Usando comando desde .compilador: {cmd_from_config}")
            # Aplicar variables de entorno
            env = os.environ.copy()
            env.update(config.get_env_vars())
            import subprocess

            result = subprocess.run(
                cmd_from_config.split(), cwd=project_dir, capture_output=True, text=True, env=env
            )
            if result.returncode == 0:
                print("✅ Compilación exitosa.")
                if result.stdout:
                    print(result.stdout)
                sys.exit(0)
            else:
                print(f"❌ Compilación falló: {result.stderr}", file=sys.stderr)
                sys.exit(1)

    # 1. Seleccionar herramienta
    if args.tool:
        tool_name = args.tool
        tools = detector.get_all_tools()
        tool = next((t for t in tools if t.get("name", "").lower() == tool_name.lower()), None)
        if not tool:
            print(f"Error: Herramienta '{tool_name}' no encontrada.", file=sys.stderr)
            sys.exit(1)
    else:
        tool = detector.get_tool_for_file(file_path)
        if not tool:
            print(
                f"Error: No se pudo detectar una herramienta adecuada para '{file_path}'.",
                file=sys.stderr,
            )
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
            print(
                f"Advertencia: Tipo de salida '{args.type}' no reconocido. Usando 'exe'.",
                file=sys.stderr,
            )
            output_type = "exe"

    # 3. Compilar
    engine = CompilationEngine()
    result = engine.compile(
        file_path=file_path,
        tool=tool,
        output_path=args.output,
        extra_args=extra_args,
        output_type=output_type,
        release_mode=args.release,
        target=args.target,
    )

    # 4. Mostrar resultados
    if result["stdout"]:
        print(result["stdout"])
    if result["stderr"]:
        print(result["stderr"], file=sys.stderr)

    if result["success"]:
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

    # Verificar si el target es nativo
    if args.target and args.target != "native":
        # Detectar si es Python con PyInstaller
        if file_path.endswith(".py"):
            # Buscar PyOxidizer
            tools = detector.get_all_tools()
            pyoxidizer = next(
                (t for t in tools if t.get("name").lower() == "PyOxidizer".lower()), None
            )

            if pyoxidizer:
                print(f"🌍 Usando PyOxidizer para {args.target}.")
                # Usar PyOxidizer como herramienta
                tool = pyoxidizer
            else:
                print(
                    f"⚠️  PyInstaller no soporta cross-compilation a {args.target}. PyOxidizer no está instalado.",
                    file=sys.stderr,
                )
                print("⚠️  Continuando con plataforma nativa.", file=sys.stderr)
                args.target = "native"

    # 1. Seleccionar herramienta de empaquetado
    if args.tool:
        tool_name = args.tool
        tools = detector.get_all_tools()
        tool = next((t for t in tools if t.get("name", "").lower() == tool_name.lower()), None)
        if not tool:
            print(f"Error: Herramienta '{tool_name}' no encontrada.", file=sys.stderr)
            sys.exit(1)
    else:
        ext = os.path.splitext(file_path)[1].lower()
        tools = detector.get_all_tools()
        packagers = [
            t for t in tools if t.get("type") == "packager" and ext in t.get("extensions", [])
        ]
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
        target=args.target,
    )

    # 4. Mostrar resultados
    if result["stdout"]:
        print(result["stdout"])
    if result["stderr"]:
        print(result["stderr"], file=sys.stderr)

    if result["success"]:
        print(f"✅ Empaquetado exitoso. Salida: {result.get('output_file', 'N/A')}")
        sys.exit(0)
    else:
        print(f"❌ Empaquetado falló con código {result.get('returncode', -1)}.", file=sys.stderr)
        sys.exit(1)


def build_project(args):
    """Compila un proyecto multi-lenguaje usando .compilador"""
    directory = args.directory
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' no existe.", file=sys.stderr)
        sys.exit(1)

    # ── CARGAR .compilador ──
    config = CompiladorConfig(directory, auto_create=True)

    # ── SI .compilador TIENE PASOS DE BUILD ──
    steps = config.get_build_steps()
    if steps:
        print("📄 Usando pasos de build desde .compilador")
        env = os.environ.copy()
        env.update(config.get_env_vars())

        for step in steps:
            language = step.get("language")
            command = step.get("command")
            if command and command != "auto":
                print(f"  🔧 {language}: {command}")
                import subprocess

                result = subprocess.run(
                    command.split(), cwd=directory, capture_output=True, text=True, env=env
                )
                if result.returncode != 0:
                    print(f"❌ Falló el paso {language}: {result.stderr}", file=sys.stderr)
                    sys.exit(1)
                if result.stdout:
                    print(result.stdout)
        print("✅ Build completado exitosamente.")
        sys.exit(0)

    # Analizar proyecto
    analyzer = ProjectAnalyzer(directory, use_ai=False)
    project_info = analyzer.analyze()

    # Crear orquestador
    from ..builder.build_orchestrator import BuildOrchestrator

    orchestrator = BuildOrchestrator(directory)
    orchestrator.create_pipeline(project_info)

    print("📦 Construyendo proyecto multi-lenguaje...")
    if orchestrator.run():
        print("✅ Construcción completada exitosamente.")
    else:
        print("❌ Construcción falló.", file=sys.stderr)
        sys.exit(1)


def enhance_config_command(args):
    """Mejora el archivo .compilador usando IA."""
    directory = args.directory
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' no es un directorio válido.", file=sys.stderr)
        sys.exit(1)

    config = CompiladorConfig(directory, auto_create=False)
    if not config or not config.config_path.exists():
        print(f"Error: No se encontró .compilador en {directory}.", file=sys.stderr)
        sys.exit(1)

    # Obtener configuración de IA
    ai_config = config.get_ai_config()
    if not ai_config.get("enabled"):
        print("Error: La IA no está habilitada en .compilador.", file=sys.stderr)
        sys.exit(1)

    # Crear cliente de IA
    from ..utils.ai_client import AIClient

    ai_client = AIClient(
        provider=ai_config.get("provider"),
        api_key=ai_config.get("api_key"),
        model=ai_config.get("model"),
    )

    if config.enhance_with_ai(ai_client):
        print("✅ Configuración mejorada con IA.")
    else:
        print("❌ No se pudo mejorar la configuración.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Módulo que proporciona listas de argumentos comunes
para diferentes herramientas de compilación/empaquetado.
"""

class ArgumentSuggester:
    # Base de datos de argumentos, indexada por nombre de herramienta (minúsculas)
    ARGUMENTS = {
        # -------------------- C / C++ compiladores --------------------
        "gcc": [
            {"flag": "-O0", "description": "Sin optimización (por defecto)", "category": "Optimización"},
            {"flag": "-O1", "description": "Optimiza para velocidad sin aumentar tiempo de compilación", "category": "Optimización"},
            {"flag": "-O2", "description": "Optimización agresiva (común)", "category": "Optimización"},
            {"flag": "-O3", "description": "Optimización muy agresiva", "category": "Optimización"},
            {"flag": "-Os", "description": "Optimiza para tamaño", "category": "Optimización"},
            {"flag": "-g", "description": "Genera información de depuración", "category": "Depuración"},
            {"flag": "-Wall", "description": "Habilita la mayoría de advertencias", "category": "Advertencias"},
            {"flag": "-Wextra", "description": "Advertencias adicionales", "category": "Advertencias"},
            {"flag": "-Werror", "description": "Trata advertencias como errores", "category": "Advertencias"},
            {"flag": "-std=c99", "description": "Usa el estándar C99", "category": "Estándar"},
            {"flag": "-std=c11", "description": "Usa el estándar C11", "category": "Estándar"},
            {"flag": "-std=c17", "description": "Usa el estándar C17", "category": "Estándar"},
            {"flag": "-I<dir>", "description": "Añade directorio a la ruta de búsqueda de includes", "category": "Inclusión"},
            {"flag": "-L<dir>", "description": "Añade directorio a la ruta de búsqueda de bibliotecas", "category": "Bibliotecas"},
            {"flag": "-l<lib>", "description": "Enlaza con la biblioteca especificada", "category": "Bibliotecas"},
            {"flag": "-D<macro>", "description": "Define una macro", "category": "Preprocesador"},
            {"flag": "-U<macro>", "description": "Cancela definición de una macro", "category": "Preprocesador"},
            {"flag": "-fPIC", "description": "Genera código independiente de posición", "category": "Generación"},
            {"flag": "-march=native", "description": "Optimiza para la arquitectura del host", "category": "Arquitectura"},
        ],
        "g++": [
            # hereda muchos de gcc, pero añade específicos de C++
            {"flag": "-std=c++11", "description": "Usa el estándar C++11", "category": "Estándar"},
            {"flag": "-std=c++14", "description": "Usa el estándar C++14", "category": "Estándar"},
            {"flag": "-std=c++17", "description": "Usa el estándar C++17", "category": "Estándar"},
            {"flag": "-std=c++20", "description": "Usa el estándar C++20", "category": "Estándar"},
            {"flag": "-fno-exceptions", "description": "Deshabilita excepciones", "category": "Excepciones"},
            {"flag": "-fno-rtti", "description": "Deshabilita RTTI", "category": "RTTI"},
        ],
        "clang": [
            # similar a gcc, con algunas opciones propias
            {"flag": "-O0", "description": "Sin optimización", "category": "Optimización"},
            {"flag": "-O1", "description": "Optimización básica", "category": "Optimización"},
            {"flag": "-O2", "description": "Optimización moderada", "category": "Optimización"},
            {"flag": "-O3", "description": "Optimización agresiva", "category": "Optimización"},
            {"flag": "-g", "description": "Información de depuración", "category": "Depuración"},
            {"flag": "-Wall", "description": "Advertencias comunes", "category": "Advertencias"},
            {"flag": "-Wextra", "description": "Advertencias extra", "category": "Advertencias"},
            {"flag": "-Werror", "description": "Advertencias como errores", "category": "Advertencias"},
            {"flag": "-std=c11", "description": "Estándar C11", "category": "Estándar"},
            {"flag": "-std=c++17", "description": "Estándar C++17", "category": "Estándar"},
            {"flag": "-fsanitize=address", "description": "Habilita sanitizador de direcciones", "category": "Sanitización"},
            {"flag": "-fsanitize=thread", "description": "Habilita sanitizador de hilos", "category": "Sanitización"},
        ],

        # -------------------- Rust --------------------
        "rustc": [
            {"flag": "-O", "description": "Optimiza código (equivalente a cargo --release)", "category": "Optimización"},
            {"flag": "-g", "description": "Incluye información de depuración", "category": "Depuración"},
            {"flag": "-C opt-level=0", "description": "Sin optimización", "category": "Optimización"},
            {"flag": "-C opt-level=1", "description": "Optimización básica", "category": "Optimización"},
            {"flag": "-C opt-level=2", "description": "Optimización más agresiva", "category": "Optimización"},
            {"flag": "-C opt-level=3", "description": "Optimización máxima", "category": "Optimización"},
            {"flag": "-C lto", "description": "Activa optimización durante el enlace", "category": "Optimización"},
            {"flag": "--target <triple>", "description": "Compila cruzado para la plataforma indicada", "category": "Destino"},
            {"flag": "-C panic=abort", "description": "Panic aborta en lugar de unwinding", "category": "Panic"},
        ],
        "cargo": [
            {"flag": "--release", "description": "Construye en modo release (optimizado)", "category": "Optimización"},
            {"flag": "--verbose", "description": "Salida detallada", "category": "Salida"},
            {"flag": "--features <lista>", "description": "Activa características específicas", "category": "Características"},
            {"flag": "--target <triple>", "description": "Construye para la plataforma destino", "category": "Destino"},
            {"flag": "--example <nombre>", "description": "Construye el ejemplo indicado", "category": "Ejemplos"},
            {"flag": "--bin <nombre>", "description": "Construye el binario indicado", "category": "Binarios"},
            {"flag": "--lib", "description": "Construye la biblioteca", "category": "Biblioteca"},
            {"flag": "--manifest-path <ruta>", "description": "Ruta al Cargo.toml", "category": "Manifiesto"},
            {"flag": "--all-features", "description": "Activa todas las características", "category": "Características"},
            {"flag": "--no-default-features", "description": "Desactiva características por defecto", "category": "Características"},
        ],

        # -------------------- Go --------------------
        "go": [
            {"flag": "-o <archivo>", "description": "Nombre del archivo de salida", "category": "Salida"},
            {"flag": "-ldflags <flags>", "description": "Opciones para el enlazador", "category": "Enlace"},
            {"flag": "-race", "description": "Activa detección de condiciones de carrera", "category": "Depuración"},
            {"flag": "-v", "description": "Salida verbosa", "category": "Salida"},
            {"flag": "-mod <modo>", "description": "Modo de descarga de módulos (readonly, vendor, mod)", "category": "Módulos"},
            {"flag": "-tags <lista>", "description": "Etiquetas de compilación", "category": "Compilación"},
            {"flag": "-trimpath", "description": "Elimina rutas del sistema en el binario", "category": "Seguridad"},
            {"flag": "-buildmode <modo>", "description": "Modo de construcción (exe, pie, c-shared, etc.)", "category": "Construcción"},
        ],

        # -------------------- Java --------------------
        "java": [
            {"flag": "-d <dir>", "description": "Directorio destino para archivos .class", "category": "Salida"},
            {"flag": "-classpath <path>", "description": "Ruta de clases", "category": "Classpath"},
            {"flag": "-sourcepath <path>", "description": "Ruta de código fuente", "category": "Origen"},
            {"flag": "-source <versión>", "description": "Compatibilidad de código fuente", "category": "Compatibilidad"},
            {"flag": "-target <versión>", "description": "Versión de la máquina virtual destino", "category": "Compatibilidad"},
            {"flag": "-Xlint", "description": "Activa advertencias recomendadas", "category": "Advertencias"},
            {"flag": "-Xlint:all", "description": "Activa todas las advertencias", "category": "Advertencias"},
            {"flag": "-verbose", "description": "Salida detallada", "category": "Salida"},
            {"flag": "-Xbootclasspath/p:<path>", "description": "Prepend a boot classpath", "category": "Avanzado"},
        ],
        "javac": [],  # se usará la misma lista que "java"

        # -------------------- .NET / C# --------------------
        "dotnet": [
            {"flag": "-c <configuration>", "description": "Configuración (Debug/Release)", "category": "Configuración"},
            {"flag": "-o <output>", "description": "Ruta de salida", "category": "Salida"},
            {"flag": "-f <framework>", "description": "Framework destino", "category": "Framework"},
            {"flag": "--no-restore", "description": "No restaurar paquetes", "category": "Restauración"},
            {"flag": "--self-contained", "description": "Publicar como auto-contenido", "category": "Publicación"},
            {"flag": "--runtime <rid>", "description": "Identificador de runtime", "category": "Publicación"},
            {"flag": "-p <property>=<value>", "description": "Establecer propiedad", "category": "Propiedades"},
        ],
        "csc": [  # compilador C# clásico
            {"flag": "/out:<file>", "description": "Archivo de salida", "category": "Salida"},
            {"flag": "/target:exe", "description": "Genera ejecutable (por defecto)", "category": "Destino"},
            {"flag": "/target:library", "description": "Genera biblioteca .dll", "category": "Destino"},
            {"flag": "/debug+", "description": "Genera información de depuración", "category": "Depuración"},
            {"flag": "/optimize+", "description": "Optimiza el código", "category": "Optimización"},
            {"flag": "/warnaserror+", "description": "Advertencias como errores", "category": "Advertencias"},
        ],

        # -------------------- Empaquetadores --------------------
        "pyinstaller": [
            {"flag": "--onefile", "description": "Empaqueta en un único ejecutable", "category": "Salida"},
            {"flag": "--onedir", "description": "Empaqueta en un directorio (por defecto)", "category": "Salida"},
            {"flag": "--windowed", "description": "No muestra consola (modo GUI)", "category": "Interfaz"},
            {"flag": "--noconsole", "description": "Igual que --windowed", "category": "Interfaz"},
            {"flag": "--icon <archivo>", "description": "Icono para el ejecutable", "category": "Icono"},
            {"flag": "--name <nombre>", "description": "Nombre del archivo de salida", "category": "Salida"},
            {"flag": "--add-data <src;dst>", "description": "Añade archivos de datos", "category": "Datos"},
            {"flag": "--hidden-import <módulo>", "description": "Añade import oculto", "category": "Imports"},
            {"flag": "--exclude-module <módulo>", "description": "Excluye módulo", "category": "Imports"},
            {"flag": "--upx-dir <ruta>", "description": "Ruta a UPX para comprimir", "category": "Compresión"},
        ],
        "pkg": [
            {"flag": "--output <archivo>", "description": "Archivo de salida", "category": "Salida"},
            {"flag": "--target <host>", "description": "Plataforma destino (node12-linux-x64, etc.)", "category": "Destino"},
            {"flag": "--options <opciones>", "description": "Opciones adicionales", "category": "Opciones"},
            {"flag": "--config <archivo>", "description": "Archivo de configuración", "category": "Configuración"},
        ],
        "python-build": [
            {"flag": "--wheel", "description": "Construye solo la rueda (wheel)", "category": "Salida"},
            {"flag": "--sdist", "description": "Construye solo el código fuente (sdist)", "category": "Salida"},
            {"flag": "--outdir <dir>", "description": "Directorio de salida", "category": "Salida"},
            {"flag": "--skip-dependency-check", "description": "Omitir verificación de dependencias", "category": "Dependencias"},
        ],
        "wasm-pack": [
            {"flag": "--target <target>", "description": "Destino (bundler, nodejs, web, etc.)", "category": "Destino"},
            {"flag": "--out-dir <dir>", "description": "Directorio de salida", "category": "Salida"},
            {"flag": "--out-name <name>", "description": "Nombre del archivo de salida", "category": "Salida"},
            {"flag": "--dev", "description": "Modo desarrollo", "category": "Modo"},
            {"flag": "--release", "description": "Modo release", "category": "Modo"},
        ],
        "emcc": [
            {"flag": "-O0", "description": "Sin optimización", "category": "Optimización"},
            {"flag": "-O1", "description": "Optimización básica", "category": "Optimización"},
            {"flag": "-O2", "description": "Optimización moderada", "category": "Optimización"},
            {"flag": "-O3", "description": "Optimización agresiva", "category": "Optimización"},
            {"flag": "-s <opción>", "description": "Opciones de emscripten", "category": "Emscripten"},
            {"flag": "--emrun", "description": "Activa soporte para emrun", "category": "Ejecución"},
        ],
    }

    @staticmethod
    def get_arguments_for_tool(tool_name):
        """
        Retorna la lista de argumentos para la herramienta dada (nombre insensible a mayúsculas).
        Si no se encuentra exactamente, intenta hacer un mapeo genérico.
        """
        key = tool_name.lower()
        # Buscar coincidencia exacta
        if key in ArgumentSuggester.ARGUMENTS:
            return ArgumentSuggester.ARGUMENTS[key]
        # Coincidencia parcial por tipo de lenguaje/herramienta
        if any(comp in key for comp in ("gcc", "g++", "clang", "cc")):
            return ArgumentSuggester.ARGUMENTS.get("gcc", [])
        if any(rust in key for rust in ("rust", "cargo")):
            return ArgumentSuggester.ARGUMENTS.get("cargo", [])
        if "go" in key:
            return ArgumentSuggester.ARGUMENTS.get("go", [])
        if "java" in key or "javac" in key:
            return ArgumentSuggester.ARGUMENTS.get("java", [])
        if "dotnet" in key or "csc" in key:
            return ArgumentSuggester.ARGUMENTS.get("dotnet", [])
        if "pyinstaller" in key:
            return ArgumentSuggester.ARGUMENTS.get("pyinstaller", [])
        if "pkg" in key:
            return ArgumentSuggester.ARGUMENTS.get("pkg", [])
        if any(wasm in key for wasm in ("wasm-pack", "emcc")):
            return ArgumentSuggester.ARGUMENTS.get("wasm-pack", [])
        # Fallback: lista vacía
        return []
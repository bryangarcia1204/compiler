 ⚙️ Compilador/Empaquetador Profesional

[![CI](https://github.com/bryangarcia1204/compiler/actions/workflows/ci.yml/badge.svg)](https://github.com/bryangarcia1204/compiler/actions/workflows/ci.yml)
[![Release](https://github.com/bryangarcia1204/compiler/actions/workflows/release.yml/badge.svg)](https://github.com/bryangarcia1204/compiler/releases)
[![codecov](https://codecov.io/gh/bryangarcia1204/compiler/branch/main/graph/badge.svg)](https://codecov.io/gh/bryangarcia1204/compiler)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/bryangarcia1204/compiler)

> **Aplicación de escritorio y CLI** que detecta automáticamente compiladores, intérpretes y empaquetadores instalados en tu sistema, permitiéndote compilar o empaquetar archivos fuente en múltiples formatos con solo unos clics.

---

## 🚀 Características

- ✅ **Detección automática** de compiladores e intérpretes (GCC, Clang, Rust, Go, Java, Python, Node.js, .NET, etc.)
- ✅ **Soporte multiplataforma** – funciona en Windows, Linux y macOS.
- ✅ **Interfaz gráfica moderna** (PyQt5) con modo oscuro y experiencia intuitiva.
- ✅ **Interfaz de línea de comandos (CLI)** para automatizar builds en scripts.
- ✅ **Múltiples tipos de salida**: ejecutables, bibliotecas dinámicas/estáticas, objetos, WASM, JAR, wheels, etc.
- ✅ **Arquitectura modular y extensible**: añade nuevos lenguajes y herramientas mediante **plugins** sin tocar el código base.
- ✅ **Parsing de errores** con mensajes claros y coloreados.
- ✅ **Sugerencias de argumentos** para cada herramienta.
- ✅ **Módulo C++ de alto rendimiento** para la detección rápida de compiladores.

---

## 🖼️ Captura de pantalla

![Compilador Profesional GUI](https://via.placeholder.com/800x450?text=Compilador+Profesional+GUI)

> *(Próximamente: captura real de la interfaz)*

---

## 📦 Instalación

### Requisitos previos

- **Python 3.8 o superior**
- **Compilador C++** con soporte para C++11 (GCC, Clang o MSVC).
- **CMake** (opcional, solo si se compila el módulo C++ manualmente).

### Instalación desde PyPI (próximamente)


    pip install compilador-profesional

Instalación desde el código fuente
bash

### Clonar el repositorio
    git clone https://github.com/bryangarcia1204/compiler.git
    cd compiler

### Crear y activar un entorno virtual (recomendado)
    python -m venv venv
    source venv/bin/activate   # Linux/macOS
    venv\Scripts\activate    # Windows

### Instalar el paquete en modo editable
    pip install -e . --no-build-isolation

  **Nota**: --no-build-isolation evita conflictos con el módulo C++ durante el desarrollo.

### Compilación del módulo C++

El módulo C++ se compila automáticamente durante la instalación con pip install -e ..
Si deseas compilarlo manualmente (por ejemplo, para depuración):


    python setup.py build_ext --inplace

En Windows, asegúrate de tener MinGW o MSVC configurado correctamente.
🧠 Uso
Interfaz Gráfica (GUI)
    
    compilador
 
O, si estás en el directorio del proyecto:

    python -m src.main

* Si al ejecutarlos les sale un error (solo a los usuarios de Windows) en una carpeta llamada utils en module les deje el DLL q tienen q usar para q funcione: Solo ponganlo en la misma carpeta q el .pyd y ya se soluciona

Pasos básicos:

    Selecciona un archivo fuente.

    Elige la herramienta deseada (se autodetecta).

    Configura el tipo de salida y argumentos adicionales.

    Haz clic en Compilar / Ejecutar o Empaquetar.

# Interfaz de Línea de Comandos (CLI)

El proyecto incluye una CLI completa para automatizar tareas.
Listar herramientas detectadas:

    compilador-cli list-tools



### Compilar con autodetección
    compilador-cli compile hola.c

### Compilar con herramienta específica y modo release
    compilador-cli compile hola.c --tool gcc --release -o hola.exe

### Compilar una biblioteca dinámica (DLL en Windows)
    compilador-cli compile hola.c --type dll -o hola.dll

### Compilar con argumentos adicionales
    compilador-cli compile hola.cpp --args "-std=c++17 -Wall"

### Empaquetar un script Python con PyInstaller
    compilador-cli package script.py --output dist/mi_app

### Empaquetar un archivo JavaScript con pkg
    compilador-cli package app.js --tool pkg

### Tipos de salida soportados (--type):
    exe, bin, dll, so, dylib, a, lib, obj, pyd, whl, jar, wasm, etc.
Consulta la lista completa en output_types.py.
🧩 Extensibilidad: Añadir nuevos lenguajes (Plugins)

# El motor de compilación está diseñado para ser extensible sin modificar el código base.

  Crea un archivo Python en "src/compilers/plugins/," por ejemplo mylang.py.

  Define una clase que herede de CompilerStrategy e implementa los métodos requeridos.

  Exporta STRATEGY_CLASS = MiClaseStrategy.

Ejemplo mínimo para un compilador ficticio "MiLang":


    mylang.py

    from ..base import CompilerStrategy

    class MiLangStrategy(CompilerStrategy):
        @property
        def tool_name(self):
            return 'milang'

        @property
        def supported_extensions(self):
            return ['.ml']

        def build_command(self, file_path, output_path=None, extra_args=None,
                          output_type='exe', release_mode=False):
            extra_args = extra_args or []
            cmd = ['milang', 'build']
            if output_path:
                cmd.extend(['-o', output_path])
            if release_mode:
                cmd.append('--release')
            if extra_args:
                cmd.extend(extra_args)
            cmd.append(file_path)
            return cmd, None, []

    STRATEGY_CLASS = MiLangStrategy

¡Así de simple! No necesitas modificar compilation_engine.py ni ningún otro archivo.
🧪 Tests

El proyecto incluye un amplio conjunto de pruebas unitarias y de integración.
bash

## Ejecutar todas las pruebas
    pytest tests/ -v

## Ejecutar con cobertura
    pytest tests/ --cov=src --cov-report=html

## Ejecutar pruebas específicas
    pytest tests/test_compilation_engine.py -v

Las pruebas se ejecutan automáticamente en GitHub Actions para Windows, Linux y macOS.
🤝 Contribución

¡Las contribuciones son bienvenidas!
Puedes ayudar de las siguientes maneras:

    Reportando errores o sugerencias en Issues.

    Añadiendo soporte para nuevas herramientas o lenguajes.

    Mejorando la documentación.

    Refactorizando o mejorando el rendimiento.

***Guía rápida***:

    Haz un fork del repositorio.

    Crea una rama para tu feature (git checkout -b feature/nueva-herramienta).

    Realiza los cambios y añade pruebas.

    Asegúrate de que todas las pruebas pasen.

    Envía un Pull Request describiendo tus cambios.

# 📄 Licencia

Este proyecto está bajo la Licencia MIT.
Consulta el archivo LICENSE para más detalles.
📬 Contacto

    Autor: Brayan M.

    Email: bgarciaguibert@gmail.com

    GitHub: bryangarcia1204

⭐ Si te gusta este proyecto, ¡no olvides darle una estrella en GitHub!
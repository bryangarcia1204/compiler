markdown

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python Version"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge&logo=opensourceinitiative&logoColor=white" alt="License MIT"/>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Multiplatform"/>
  <img src="https://img.shields.io/badge/UI-PyQt5-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt5"/>
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=for-the-badge" alt="PRs Welcome"/>
</p>

<h1 align="center">🛠️ Compilador / Empaquetador Profesional</h1>

<p align="center">
  <strong>Compila y empaqueta código fuente en múltiples lenguajes con un solo clic.</strong><br/>
  Detecta automáticamente las herramientas instaladas y te ofrece las opciones de salida más adecuadas.
</p>

<br/>

## 📖 Tabla de Contenidos

- [🚀 Características](#-características)
- [📸 Capturas de pantalla](#-capturas-de-pantalla)
- [⚙️ Instalación](#️-instalación)
  - [Requisitos previos](#requisitos-previos)
  - [Pasos de instalación](#pasos-de-instalación)
- [🖥️ Uso](#️-uso)
  - [Interfaz gráfica](#interfaz-gráfica)
  - [Línea de comandos](#línea-de-comandos)
- [📁 Estructura del proyecto](#-estructura-del-proyecto)
- [🧪 Pruebas](#-pruebas)
- [🤝 Contribuir](#-contribuir)
- [📄 Licencia](#-licencia)
- [📬 Contacto](#-contacto)

---

## 🚀 Características

| Característica | Descripción |
|----------------|-------------|
| 🔍 **Detección inteligente** | Escanea tu sistema en busca de compiladores (GCC, Clang, MSVC, Rust, Go, Java, C#), intérpretes (Python, Node.js) y empaquetadores (PyInstaller, pkg, wasm-pack, etc.). |
| 🎯 **Filtrado dinámico** | Los tipos de salida disponibles se adaptan automáticamente al lenguaje y a la herramienta seleccionada. |
| ⚡ **Multiplataforma** | Funciona en **Windows**, **Linux** y **macOS** sin modificaciones. |
| 🎨 **Interfaz moderna** | Diseño oscuro y limpio con PyQt5, con soporte para temas y atajos de teclado. |
| 💾 **Configuración persistente** | Guarda automáticamente el último archivo, herramienta, argumentos y modo de lanzamiento (Release/Debug). |
| 📦 **Múltiples formatos de salida** | Genera ejecutables, bibliotecas dinámicas/estáticas, objetos, módulos Python, paquetes, WASM, APK, JAR, etc. |
| 🧩 **Sugerencias de argumentos** | Ofrece una lista de flags comunes para cada herramienta (GCC, Clang, Rustc, etc.). |
| 🛡️ **Manejo de errores** | Analiza y muestra errores de compilación con colores y contexto (línea, archivo, tipo). |
| 🧪 **Pruebas unitarias** | Incluye un conjunto básico de pruebas para asegurar el correcto funcionamiento. |

---

## 📸 Capturas de pantalla

> *Próximamente: añade aquí una imagen de la interfaz principal.*

<p align="center">
  <img src="screenshot.png" alt="Interfaz principal" width="800"/>
  <br/>
  <em>Ventana principal del Compilador Profesional.</em>
</p>

<p align="center">
  <img src="screenshot_arguments.png" alt="Sugerencias de argumentos" width="600"/>
  <br/>
  <em>Diálogo de sugerencias de argumentos para GCC.</em>
</p>

---

## ⚙️ Instalación

### Requisitos previos

- **Python 3.8 o superior** (descargar desde [python.org](https://python.org))
- **Compilador C++** (necesario para compilar el módulo de detección):
  - Windows: [MinGW-w64](https://www.mingw-w64.org/) o [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
  - Linux: `g++` o `clang++` (instalar con `sudo apt install build-essential` en Debian/Ubuntu)
  - macOS: `clang++` (Xcode Command Line Tools: `xcode-select --install`)

### Pasos de instalación

1. **Clona el repositorio**

   ```bash
   git clone https://github.com/tu-usuario/compilador-profesional.git
   cd compilador-profesional

    (Opcional) Crea un entorno virtual
    bash

    python -m venv venv
    source venv/bin/activate        # Linux/macOS
    venv\Scripts\activate           # Windows

    Instala el paquete en modo editable
    bash

    pip install -e .

    Esto instalará todas las dependencias (PyQt5, pybind11, etc.) y compilará automáticamente el módulo C++ en tu sistema. Si la compilación falla, asegúrate de tener instalado un compilador C++ y vuelve a intentarlo.

    Verifica la instalación
    bash

    python -c "import src.cpp_module; print('✅ Módulo C++ cargado correctamente')"

🖥️ Uso
Interfaz gráfica

La forma más sencilla de usar el compilador es a través de su interfaz gráfica.
bash

compilador

O directamente:
bash

python -m src.main

Pasos básicos:

    Haz clic en Seleccionar archivo... y elige tu código fuente.

    El programa detectará automáticamente el lenguaje y te mostrará las herramientas disponibles.

    Selecciona una herramienta de la lista desplegable.

    Opcionalmente, elige el tipo de salida (ejecutable, biblioteca, etc.) y añade argumentos adicionales.

    Marca Build Release para optimización (si aplica).

    Elige entre Compilar / Ejecutar (para lenguajes interpretados) o Empaquetar (para generar un ejecutable independiente).

    Haz clic en el botón principal para iniciar el proceso.

    Revisa la salida en el panel de logs, donde los errores se muestran en rojo y las advertencias en naranja.

Línea de comandos (futura integración):

    Próximamente: soporte para ejecución desde terminal con argumentos.

bash:

    compilador --file main.py --tool PyInstaller --output dist/ --release

📁 Estructura del proyecto:
text

    compilador-profesional/
    ├── src/                          # Código fuente Python
    │   ├── __init__.py
    │   ├── main.py                  # Punto de entrada (interfaz PyQt5)
    │   ├── argument_suggester.py    # Base de datos de flags para cada herramienta
    │   ├── compilation_engine.py    # Ejecución de comandos de compilación/empaquetado
    │   ├── compiler_detector.py     # Detección de herramientas instaladas
    │   ├── error_parser.py          # Análisis y formateo de errores de compilación
    │   ├── language_detector.py     # Identificación del lenguaje por extensión
    │   ├── logger.py                # Sistema de logging (consola + archivo)
    │   └── output_types.py          # Mapa de nombres de salida a códigos internos
    │
    ├── cpp_module/                   # Módulo C++ para detección de compiladores
    │   ├── detector.h
    │   ├── detector.cpp             # Implementación de detección (GCC, Clang, etc.)
    │   ├── bindings.cpp             # Enlace con pybind11
    │   └── setup.py                 # Script de compilación independiente
    │
    ├── tests/                        # Pruebas unitarias
    │   ├── __init__.py
    │   └── test_detector.py         # Pruebas básicas del detector
    │
    ├── .gitignore                    # Archivos ignorados por Git
    ├── LICENSE                       # Licencia MIT
    ├── README.md                     # Este archivo
    ├── requirements.txt              # Dependencias Python
    ├── setup.py                      # Compilación e instalación del paquete
    └── pyproject.toml                # Configuración moderna del proyecto

🧪 Pruebas

Para ejecutar las pruebas unitarias:
bash

    pytest tests/

O, si no tienes pytest instalado:
bash

    python -m unittest discover tests

Las pruebas verifican la detección de herramientas y el correcto funcionamiento de los módulos principales.
🤝 Contribuir

Las contribuciones son muy bienvenidas. Para colaborar:

    Haz un fork del repositorio.

    Crea una rama para tu funcionalidad o corrección:
    bash

    git checkout -b feature/nueva-funcionalidad

    Realiza tus cambios y asegúrate de que las pruebas pasen.

    Haz commit de tus cambios con un mensaje claro:
    bash

    git commit -m "feat: añade soporte para compilador XYZ"

    Sube tu rama a GitHub:
    bash

    git push origin feature/nueva-funcionalidad

    Abre un Pull Request describiendo tus cambios.

Guía de estilo

    Sigue PEP 8 para el código Python.

    Usa Google Style Docstrings para documentar funciones y clases.

    Asegúrate de que todas las pruebas pasen antes de enviar un PR.

📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT. Consulta el archivo LICENSE para más detalles.
text

MIT License

    Copyright (c) 2025 [Brayan M.]

    Se concede permiso, de forma gratuita, a cualquier persona que obtenga una copia
    de este software y de los archivos de documentación asociados (el "Software"),
    para tratar el Software sin restricciones, incluidos, sin limitación, los derechos
    de uso, copia, modificación, fusión, publicación, distribución, sublicencia y/o
    venta de copias del Software, y para permitir a las personas a las que se les
    proporcione el Software que lo hagan, sujeto a las siguientes condiciones:

    El aviso de copyright anterior y este aviso de permiso se incluirán en todas
    las copias o partes sustanciales del Software.

    EL SOFTWARE SE PROPORCIONA "TAL CUAL", SIN GARANTÍA DE NINGÚN TIPO, EXPRESA O
    IMPLÍCITA, INCLUYENDO PERO NO LIMITADO A GARANTÍAS DE COMERCIABILIDAD,
    ADECUACIÓN PARA UN PROPÓSITO PARTICULAR Y NO INFRACCIÓN. EN NINGÚN CASO LOS
    AUTORES O TITULARES DEL COPYRIGHT SERÁN RESPONSABLES DE NINGUNA RECLAMACIÓN,
    DAÑOS U OTRAS RESPONSABILIDADES, YA SEA EN UNA ACCIÓN DE CONTRATO, AGRAVIO O
    DE OTRO TIPO, QUE SURJA DE O EN RELACIÓN CON EL SOFTWARE O EL USO U OTROS
    ACUERDOS EN EL SOFTWARE.

📬 Contacto

    Autor: Brayan M.

    Correo: tu@email.com

    GitHub: github.com/tu-usuario/compilador-profesional

Si tienes preguntas, sugerencias o encuentras algún error, no dudes en abrir un issue o contactarme directamente.
<p align="center"> <strong>¡Gracias por usar el Compilador Profesional! 🚀</strong> </p> ```
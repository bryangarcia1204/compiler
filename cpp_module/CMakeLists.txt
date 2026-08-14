# Versión mínima de CMake requerida para las funcionalidades utilizadas.
# Se recomienda una versión reciente para mejor soporte y características.
cmake_minimum_required(VERSION 3.15)

# Nombre del proyecto y lenguajes a habilitar.
# CXX indica que usaremos C++.
project(cpp_module LANGUAGES CXX)

# Establecer el estándar C++ a usar.
# C++17 es una buena opción moderna. C++11 es el mínimo requerido por pybind11.
# Se recomienda usar C++17 o C++20 si el compilador lo soporta.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF) # Deshabilitar extensiones del compilador para mayor portabilidad y conformidad.

# --- Configuración para Pybind11 ---
# Buscar el paquete pybind11. Esto asume que pybind11 está instalado en el sistema
# o que se puede encontrar a través de CMAKE_PREFIX_PATH.
# Si pybind11 no está instalado globalmente, se puede añadir como un submódulo Git
# o especificar su ruta con find_package(pybind11 CONFIG HINTS /path/to/pybind11).
find_package(pybind11 CONFIG REQUIRED)

# Definir las fuentes del módulo C++.
# Se incluyen los archivos .cpp y .h necesarios para la compilación.
# Es una buena práctica organizar los archivos fuente en un subdirectorio como 'src/'.
set(MODULE_SOURCES
    bindings.cpp
    detector.cpp
    detector.h
)

# Añadir el módulo de Python.
# pybind11_add_module es una función proporcionada por pybind11 que simplifica la creación
# de módulos de extensión de Python. Genera el nombre de archivo correcto (.pyd en Windows).
# El primer argumento es el nombre del módulo Python (cómo se importará en Python).
# El segundo argumento es el tipo de módulo (MODULE para un módulo de extensión).
# Los argumentos siguientes son los archivos fuente.
pybind11_add_module(cpp_module MODULE ${MODULE_SOURCES})

# Opciones de compilación específicas para el módulo.
# Estas opciones se aplican solo a los archivos fuente del módulo.
# Se configuran advertencias para un código más robusto y depuración.
# Dado que se usa MinGW, las opciones son para compiladores tipo GCC/Clang.
if(CMAKE_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(cpp_module PRIVATE
        -Wall               # Habilitar todas las advertencias comunes.
        -Wextra             # Habilitar advertencias adicionales.
        -Wpedantic          # Advertir sobre construcciones que no son estrictamente conformes al estándar.
        -Werror             # Tratar las advertencias como errores (útil para CI/CD).
        -g                  # Generar información de depuración.
        -O2                 # Nivel de optimización para Release builds (se puede ajustar).
    )
endif()

# Opcional: Enlazar bibliotecas externas si fueran necesarias.
# Por ejemplo, si 'detector.cpp' usara alguna función de una biblioteca externa.
# target_link_libraries(cpp_module PRIVATE some_library)

# --- Configuración de instalación (opcional) ---
# Si se desea instalar el módulo después de la compilación.
# install(TARGETS cpp_module DESTINATION ${CMAKE_INSTALL_LIBDIR})

# --- Configuración del tipo de construcción ---
# Esto se puede controlar también al invocar CMake con -DCMAKE_BUILD_TYPE=Release.
# Se establece un valor por defecto si no se especifica.
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Choose the type of build, options are: Debug Release MinSizeRel RelWithDebInfo." FORCE)
endif()

# --- Manejo de libwinpthread-1.dll ---
# Esta DLL es una dependencia de tiempo de ejecución para MinGW en Windows.
# Necesita estar junto al módulo .pyd o en el PATH del sistema para que el módulo funcione.
# Una forma de gestionarlo es copiarla al directorio de salida del módulo.
# Esto es un ejemplo, la ruta a la DLL puede variar.
# Se asume que libwinpthread-1.dll está en el mismo directorio que CMakeLists.txt.
# Para una solución más robusta, se podría buscar en el PATH de MinGW.
if(WIN32)
    find_file(WINPTHREAD_DLL libwinpthread-1.dll
        PATHS ${CMAKE_CURRENT_SOURCE_DIR}
        NO_DEFAULT_PATH
    )
    if(WINPTHREAD_DLL)
        add_custom_command(
            TARGET cpp_module POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different ${WINPTHREAD_DLL} $<TARGET_FILE_DIR:cpp_module>
            COMMENT "Copiando libwinpthread-1.dll al directorio de salida del módulo"
        )
    else()
        message(WARNING "libwinpthread-1.dll no encontrada. Asegúrese de que esté en el PATH o junto al módulo .pyd.")
    endif()
endif()

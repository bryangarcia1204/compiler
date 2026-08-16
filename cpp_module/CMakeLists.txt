# Mínima versión de CMake requerida
cmake_minimum_required(VERSION 3.15)

# Nombre del proyecto
project(cpp_module LANGUAGES CXX)

# Habilitar C++17 (o una versión más moderna si es posible)
# Esto es una recomendación para aprovechar características modernas del lenguaje.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Buscar Pybind11
# Se asume que pybind11 está instalado en el entorno o se puede encontrar.
# Si no, se podría necesitar especificar PYBIND11_DIR o incluirlo como un submódulo.
find_package(pybind11 CONFIG REQUIRED)

# Añadir las librerías de pybind11
# pybind11_add_module es una función conveniente proporcionada por pybind11
# para crear módulos de extensión de Python.
pybind11_add_module(detector_module MODULE bindings.cpp detector.cpp)

# Incluir directorios para los headers (si los hubiera fuera del directorio actual)
# Por ejemplo, si detector.h estuviera en un subdirectorio 'include'.
# target_include_directories(detector_module PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# Enlazar librerías adicionales si son necesarias
# Por ejemplo, si detector.cpp o bindings.cpp usaran otras librerías.
# target_link_libraries(detector_module PRIVATE some_library)

# Si libwinpthread-1.dll es una dependencia de tiempo de ejecución y no se enlaza estáticamente,
# se podría necesitar copiarla al directorio de salida.
# Esto es un ejemplo y podría variar dependiendo de cómo se gestione la DLL.
# if(WIN32)
#     find_library(WINPTHREAD_LIBRARY NAMES libwinpthread-1.dll PATHS ${CMAKE_CURRENT_SOURCE_DIR})
#     if(WINPTHREAD_LIBRARY)
#         add_custom_command(TARGET detector_module POST_BUILD
#             COMMAND ${CMAKE_COMMAND} -E copy_if_different
#             $<TARGET_FILE:WINPTHREAD_LIBRARY>
#             $<TARGET_FILE_DIR:detector_module>
#             COMMENT "Copying libwinpthread-1.dll to build directory"
#         )
#     endif()
# endif()

# Instalar el módulo para que pueda ser encontrado por Python
install(TARGETS detector_module DESTINATION ${CMAKE_INSTALL_LIBDIR})

# Configuración para el archivo setup.py (si se usa CMake para generar setup.py o para informar)
# Aunque setup.py ya existe, CMakeLists.txt puede ser la fuente principal de verdad para la compilación.
# Se recomienda usar uno u otro como sistema de compilación principal.
# Si se usa CMake, setup.py podría simplemente llamar a CMake.
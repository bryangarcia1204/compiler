import os
from typing import List, Tuple, Optional, Any, Dict
from ..base import CompilerStrategy
from ...target_manager import TargetManager

class GPPStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'g++'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.cpp', '.cc', '.cxx']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False,
        target: str = 'native'   # <-- NUEVO: target por defecto
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ['g++']
        out = output_path or os.path.splitext(file_path)[0]

        # ── CROSS-COMPILATION ──
        if target != 'native':
            target_info = TargetManager.get_target(target)
            if target_info:
                # Verificar si hay herramientas
                available = TargetManager.get_available_tools()
                tools = available.get(target, [])

                if 'zig' in tools:
                    # Usar Zig como compilador cruzado
                    cmd = ['zig', 'cc']
                    zig_target = TargetManager.get_zig_target(target)
                    if zig_target:
                        cmd.extend(['-target', zig_target])
                else:
                    # Usar MinGW o cross-gcc
                    prefix = TargetManager.get_compiler_prefix(target)
                    if prefix:
                        cmd = [f'{prefix}g++']

        if output_type in ('exe', 'bin', 'go-bin', 'rust-bin', 'cargo-release'):
            out = out + ('.exe' if os.name == 'nt' and not out.endswith('.exe') else '')
        elif output_type in ('dll', 'so', 'dylib'):
            ext = {'dll': '.dll', 'so': '.so', 'dylib': '.dylib'}[output_type]
            out = out + ext if not out.endswith(ext) else out
        elif output_type in ('obj', 'o'):
            out = out + ('.obj' if os.name == 'nt' else '.o')
        elif output_type == 'pyd':
            out = out + ('.pyd' if os.name == 'nt' else '.so')

        if output_type in ('dll', 'so', 'dylib', 'pyd'):
            cmd.append('-shared')
        if output_type in ('obj',):
            cmd.append('-c')

        if release_mode:
            cmd.append('-O2')
        else:
            cmd.append('-g')

        cmd.extend(['-o', out, file_path])
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, []

    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
            """
            Genera archivos de configuración para C++.
            """
            project_name = os.path.basename(project_info.get('project_dir', 'mi_proyecto'))
            main_file = project_info.get('main_file', 'main.cpp')
            src_name = os.path.basename(main_file) if main_file else f'main.cpp'
            has_cmake = any('CMakeLists.txt' in f for f in project_info.get('files', []))

            files = {}

            # ── Makefile ──
            files['Makefile'] = f'''# Makefile para proyecto C++
# Generado por Compilador Profesional

CXX = g++
CXXFLAGS = -Wall -Wextra -O2 -std=c++17
LDFLAGS =

TARGET = {project_name}
SRCS = {src_name}
OBJS = $(SRCS:.cpp=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
\t$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

%.o: %.cpp
\t$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
\trm -f $(OBJS) $(TARGET)

run: $(TARGET)
\t./$(TARGET)

.PHONY: all clean run
'''

        # ── CMakeLists.txt ── (solo si no existe)
            if not has_cmake:
                files['CMakeLists.txt'] = f'''cmake_minimum_required(VERSION 3.10)
project({project_name} VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

file(GLOB SOURCES "src/*.cpp" "src/*.cc" "src/*.cxx")

add_executable({project_name} ${{SOURCES}})

target_include_directories({project_name} PRIVATE include)
'''

            # ── .gitignore ──
            files['.gitignore'] = """*.o
*.obj
*.exe
*.out
*.so
*.dll
*.a
*.lib
build/
"""

            return files


STRATEGY_CLASS = GPPStrategy
# src/compilers/builtin/gcc.py
import os
from typing import List, Tuple, Optional, Any, Dict
from ..base import CompilerStrategy
from ...utils.target_manager import TargetManager


class GCCStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'gcc'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.c']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ['gcc']
        out = output_path or os.path.splitext(file_path)[0]
        post_actions = []

        # ── CROSS-COMPILATION ──
        if target != 'native':
            target_info = TargetManager.get_target(target)
            if target_info:
                available = TargetManager.get_available_tools()
                tools = available.get(target, [])

                if 'zig' in tools:
                    cmd = ['zig', 'cc']
                    zig_target = TargetManager.get_zig_target(target)
                    if zig_target:
                        cmd.extend(['-target', zig_target])
                else:
                    prefix = TargetManager.get_compiler_prefix(target)
                    if prefix:
                        cmd = [f'{prefix}gcc']

        if release_mode:
            cmd.append('-O2')
        else:
            cmd.append('-g')

        if output_type == 'obj':
            cmd.append('-c')
        elif output_type in ('dll', 'so', 'dylib'):
            cmd.append('-shared')
        elif output_type in ('a', 'lib'):
            cmd.append('-c')
            if out:
                obj_path = out.replace('.a', '.o').replace('.lib', '.obj')
                cmd.extend(['-o', obj_path])
                post_actions = [('archive', (obj_path, out))]
            else:
                post_actions = []
        else:
            post_actions = []

        if out and output_type not in ('a', 'lib'):
            cmd.extend(['-o', out])

        if extra_args:
            cmd.extend(extra_args)

        cmd.append(file_path)
        return cmd, None, post_actions

    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
        """
        Genera archivos de configuración para C.
        """
        project_name = os.path.basename(project_info.get('project_dir', 'mi_proyecto'))
        main_file = project_info.get('main_file', 'main.c')
        src_name = os.path.basename(main_file) if main_file else 'main.c'
        has_cmake = any('CMakeLists.txt' in f for f in project_info.get('files', []))

        files = {}

        # ── Makefile ──
        files['Makefile'] = f'''# Makefile para proyecto C
# Generado por Compilador Profesional

CC = gcc
CFLAGS = -Wall -Wextra -O2 -std=c11
LDFLAGS =

TARGET = {project_name}
SRCS = {src_name}
OBJS = $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
\t$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

%.o: %.c
\t$(CC) $(CFLAGS) -c $< -o $@

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

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

file(GLOB SOURCES "src/*.c")

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


STRATEGY_CLASS = GCCStrategy

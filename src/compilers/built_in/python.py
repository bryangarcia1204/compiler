# src/compilers/builtin/python.py
from typing import List, Tuple, Optional, Any, Dict
import os
from ..base import CompilerStrategy
from ...utils import logger

log = logger.Logger()


class PythonStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'python'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.py']

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
        cmd = ['python', file_path]
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, []

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        if target != 'native':
            log.warning(f"[Python] PyInstaller no soporta cross-compilation a {target}. Se usará el target nativo.")
        cmd = ['pyinstaller', '--onefile', '--noconsole']
        if output_path:
            base_dir = os.path.dirname(output_path)
            if base_dir:
                cmd.extend(['--distpath', base_dir])
            if os.path.splitext(output_path)[1]:
                output_name = os.path.splitext(os.path.basename(output_path))[0]
                cmd.extend(['--name', output_name])
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(file_path)
        return cmd, None, []

    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
        """
        Genera archivos de configuración para Python, incluyendo
        flags de compilación cruzada si es necesario.
        """
        project_name = os.path.basename(project_info.get('project_dir', 'mi_proyecto'))
        dependencies = list(project_info.get('dependencies', set()))[:10]
        project_type = project_info.get('project_type', 'application')

        files = {}

        # ── requirements.txt ──
        req_lines = ['# Dependencias del proyecto', '# Generado por Compilador Profesional', '']
        if dependencies:
            req_lines.extend(dependencies)
        else:
            req_lines.extend(['# Añade aquí tus dependencias', '', '# Ejemplo:', '# numpy>=1.21.0'])
        files['requirements.txt'] = '\n'.join(req_lines)

        # ── .gitignore ──
        files['.gitignore'] = self._gitignore_python()

        # ── setup.py (si es librería o extensión) ──
        if project_type in ('library', 'extension'):
            # Si hay targets múltiples, añadir comentario en setup.py
            target_info = ""
            if targets and len(targets) > 1:
                target_info = f"\n# Targets: {', '.join(targets)}"
            files['setup.py'] = self._setup_py(project_name, project_info) + target_info

        return files

    def _gitignore_python(self) -> str:
        return """__pycache__/
*.py[cod]
*.so
*.pyd
*.dll
venv/
.env
.venv
dist/
build/
*.egg-info/
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/
"""

    def _setup_py(self, name: str, info: Dict) -> str:
        has_cpp = any(f.get('language') in ('c', 'cpp') for f in info.get('source_files', []))
        if has_cpp:
            return f'''from setuptools import setup, Extension
import pybind11

ext_module = Extension(
    '{name}',
    sources=['src/{name}.cpp'],
    include_dirs=[pybind11.get_include()],
    language='c++',
    extra_compile_args=['-std=c++11', '-O3'],
    extra_link_args=['-shared', '-fPIC'],
)

setup(
    name='{name}',
    ext_modules=[ext_module],
    install_requires=['pybind11>=3.1'],
)
'''
        return f'''from setuptools import setup, find_packages

setup(
    name='{name}',
    version='0.1.0',
    description='Descripción del proyecto',
    author='Tu Nombre',
    packages=find_packages(),
    install_requires=[],
    python_requires='>=3.8',
)
'''


STRATEGY_CLASS = PythonStrategy

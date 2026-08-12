# src/project_generator.py
"""
Módulo para generar archivos de configuración usando plantillas o IA.
"""

import os
from typing import Dict, List, Optional, Any

from .template_loader import TemplateLoader
from .ai_client import AIClient
from . import logger

log = logger.Logger()


class ProjectGenerator:
    """
    Genera archivos de configuración (Makefile, Cargo.toml, etc.) usando
    plantillas predefinidas o IA.
    """

    # Mapeo de extensiones a tipos de proyecto (para fallback)
    EXTENSION_MAP = {
        '.c': 'c', '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
        '.h': 'c', '.hpp': 'cpp', '.hxx': 'cpp',
        '.rs': 'rust', '.go': 'go', '.py': 'python',
        '.js': 'node', '.ts': 'node', '.java': 'java',
        '.cs': 'dotnet', '.fs': 'dotnet', '.vb': 'dotnet',
    }

    def __init__(
        self,
        use_ai: bool = False,
        provider: str = "deepseek",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.use_ai = use_ai
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

        # Inicializar AIClient si se usa IA
        self.ai_client = None
        if self.use_ai and self.api_key:
            self.ai_client = AIClient(
                provider=self.provider,
                api_key=self.api_key,
                model=self.model,
                base_url=self.api_base
            )
            log.info(f"[ProjectGenerator] IA inicializada: {provider} - {self.model}")

        # TemplateLoader siempre disponible
        self.template_loader = TemplateLoader(
            use_ai=self.use_ai, 
            provider=self.provider, 
            api_key=self.api_key, 
            api_base=self.api_base,
            model=self.model
            )

    # ──────────────────────────────────────────────────────────
    # 1. GENERACIÓN DE ARCHIVOS (PUNTO DE ENTRADA)
    # ──────────────────────────────────────────────────────────
    def generate_config_files(self, project_info: Dict, custom_prompt: str = "") -> Dict[str, str]:
        """
        Genera archivos de configuración usando plantillas o IA.

        Args:
            project_info: Diccionario con información del proyecto (del ProjectAnalyzer)
            custom_prompt: Prompt personalizado para la IA

        Returns:
            Dict con {nombre_archivo: contenido}
        """
        # Extraer información del proyecto
        language = project_info.get('main_language') or project_info.get('language') or project_info.get('type', 'python')
        project_name = os.path.basename(project_info.get('project_dir', 'mi_proyecto'))
        project_type = project_info.get('project_type', 'application')
        binary_target = project_info.get('binary_target')
        files = project_info.get('files', [])
        source_files = project_info.get('source_files', [])
        dependencies = list(project_info.get('dependencies', set()))

        # Usar IA si está disponible y hay prompt personalizado
        if self.use_ai and self.ai_client and self.ai_client.client:
            log.info(f"[ProjectGenerator] Generando con IA para {language} (proyecto: {project_name})")

            # Construir contexto para la IA
            context = self._build_ai_context(project_info, language, project_name, project_type, binary_target, files, dependencies)

            # Generar con IA
            return self._generate_with_ai(context, language, custom_prompt)

        # Si no hay IA, usar plantillas
        log.info(f"[ProjectGenerator] Generando con plantillas para {language}")
        result = self._generate_with_templates(language, project_name, project_type, project_info)

        # Si no hay plantillas para ese lenguaje, usar fallback
        if not result:
            result = self._generate_fallback_templates(language, project_name, project_type, project_info)

        return result

    # ──────────────────────────────────────────────────────────
    # 2. GENERACIÓN CON IA
    # ──────────────────────────────────────────────────────────
    def _build_ai_context(self, project_info: Dict, language: str, project_name: str, project_type: str, binary_target: str, files: List, dependencies: List) -> str:
        """Construye el contexto para la IA."""
        # Obtener ejemplos de plantillas existentes
        existing_templates = self.template_loader.get_all_templates_for_language(language)
        template_examples = "\n".join(
            f"--- {name} ---\n{content[:300]}...\n--- FIN ---"
            for name, content in list(existing_templates.items())[:3]
        )

        # Lista de archivos principales
        main_files = project_info.get('main_files', [])
        main_file_list = '\n'.join(f'  - {os.path.basename(f)}' for f in main_files[:5])

        return f"""
**Proyecto:** {project_name}
**Lenguaje principal:** {language}
**Tipo de proyecto:** {project_type}
**Target binario:** {binary_target or 'Ninguno'} (ej: pyd, so, dll, exe)

**Archivos fuente:** {len(files)}
**Archivos principales:**
{main_file_list or '  - No detectados'}

**Dependencias detectadas:**
{chr(10).join(f'  - {dep}' for dep in dependencies[:10]) if dependencies else '  - Ninguna'}

**Plantillas existentes para {language}:**
{chr(10).join(f'  - {name}' for name in existing_templates.keys()) if existing_templates else '  - No hay plantillas predefinidas'}

**Ejemplos de formato:**
{template_examples if template_examples else '  - (No hay ejemplos disponibles)'}
"""

    def _generate_with_ai(self, context: str, language: str, custom_prompt: str= None) -> Dict[str, str]:
        """Genera archivos usando el AIClient."""
        if not self.ai_client:
            log.warning("[ProjectGenerator] AIClient no disponible, usando plantillas")
            return {}

        # Construir prompt completo
        prompt = f"""
Eres un experto en desarrollo de software especializado en generar archivos de configuración.

**Contexto del proyecto:**
{context}

**Instrucciones adicionales:**
{custom_prompt if custom_prompt else 'Genera los archivos de configuración típicos para este proyecto.'}

**Requerimientos:**
1. Genera los archivos de configuración más relevantes para este proyecto.
2. Sigue las mejores prácticas para {language}.
3. Incluye comentarios explicativos cuando sea necesario.

**Formato de respuesta:** Cada archivo debe estar delimitado por:
--- NOMBRE_ARCHIVO ---
contenido del archivo
--- FIN ---
"""

        try:
            # Usar el AIClient para generar
            response = self.ai_client.chat([
                {"role": "system", "content": "Eres un experto en desarrollo de software y generación de archivos de configuración."},
                {"role": "user", "content": prompt}
            ], temperature=0.7, max_tokens=500, extra_body={"thinking": {"type": "enabled"}} if self.provider == "deepseek" else {})

            if response:
                return self._parse_ai_response(response, language)

            log.warning("[ProjectGenerator] No se recibió respuesta de IA")
            return self._generate_with_templates(language, "", "", {})

        except Exception as e:
            log.error(f"[ProjectGenerator] Error con IA: {e}")
            return self._generate_with_templates(language, "", "", {})

    def _parse_ai_response(self, content: str, language: str) -> Dict[str, str]:
        """Parsea la respuesta de la IA en un diccionario de archivos."""
        import re
        result = {}
        pattern = r'---\s*([A-Za-z0-9_.-]+)\s*---\s*([\s\S]*?)\s*---\s*FIN\s*---'
        matches = re.findall(pattern, content)

        for filename, file_content in matches:
            result[filename] = file_content.strip()

        if not result:
            log.warning("[ProjectGenerator] No se pudo parsear respuesta de IA, usando plantillas")
            return self._generate_with_templates(language, "", "", {})

        return result

    # ──────────────────────────────────────────────────────────
    # 3. GENERACIÓN CON PLANTILLAS (COMPLETO)
    # ──────────────────────────────────────────────────────────
    def _generate_with_templates(self, language: str, project_name: str, project_type: str, project_info: Dict) -> Dict[str, str]:
        """Genera archivos usando plantillas predefinidas del TemplateLoader."""
        result = self.template_loader.generate_with_templates(
            language=language,
            project_name=project_name,
            custom_prompt=""
        )

        # Si no hay plantillas para ese lenguaje, usar fallback específico
        if not result:
            result = self._generate_fallback_templates(language, project_name, project_type, project_info)

        return result

    # ──────────────────────────────────────────────────────────
    # 4. PLANTILLAS DE FALLBACK (ESPECÍFICAS POR LENGUAJE)
    # ──────────────────────────────────────────────────────────
    def _generate_fallback_templates(self, language: str, project_name: str, project_type: str, project_info: Dict) -> Dict[str, str]:
        """Genera plantillas de respaldo cuando no hay plantillas específicas en TemplateLoader."""
        result = {}

        # Obtener archivos fuente
        source_files = project_info.get('source_files', [])
        main_files = project_info.get('main_files', [])
        main_file = main_files[0] if main_files else None

        # Detectar si hay archivos C/C++
        has_cpp = any(f.get('language') in ('c', 'cpp') for f in source_files)

        # ── PYTHON ──
        if language == 'python':
            result['requirements.txt'] = self._make_requirements_txt(project_info)
            if has_cpp or project_type == 'binary_extension':
                result['setup.py'] = self._make_setup_py(project_name, project_info)
            result['.gitignore'] = self._make_gitignore('python')

        # ── RUST ──
        elif language == 'rust':
            result['Cargo.toml'] = self._make_cargo_toml(project_name, project_info)
            result['.gitignore'] = self._make_gitignore('rust')

        # ── GO ──
        elif language == 'go':
            result['go.mod'] = self._make_go_mod(project_name, project_info)
            result['.gitignore'] = self._make_gitignore('go')

        # ── C/C++ ──
        elif language in ('c', 'cpp'):
            result['Makefile'] = self._make_makefile(project_name, language, main_file)
            result['.gitignore'] = self._make_gitignore('c')
            if has_cpp:
                result['CMakeLists.txt'] = self._make_cmake(project_name, language)

        # ── JAVA ──
        elif language == 'java':
            result['pom.xml'] = self._make_pom_xml(project_name, project_info)
            result['.gitignore'] = self._make_gitignore('java')

        # ── NODE.JS ──
        elif language == 'node':
            result['package.json'] = self._make_package_json(project_name, main_file)
            result['.gitignore'] = self._make_gitignore('node')

        # ── C# / .NET ──
        elif language == 'dotnet':
            result[f'{project_name}.csproj'] = self._make_csproj(project_name)
            result['.gitignore'] = self._make_gitignore('dotnet')

        return result

    # ──────────────────────────────────────────────────────────
    # 5. PLANTILLAS INDIVIDUALES
    # ──────────────────────────────────────────────────────────
    def _make_requirements_txt(self, info: Dict) -> str:
        deps = list(info.get('dependencies', set()))[:10]
        lines = ['# Dependencias del proyecto', '# Generado por Compilador Profesional', '']
        if deps:
            lines.extend(deps)
        else:
            lines.extend(['# Añade aquí tus dependencias', '', '# Ejemplo:', '# numpy>=1.21.0'])
        return '\n'.join(lines)

    def _make_setup_py(self, name: str, info: Dict) -> str:
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

    def _make_cargo_toml(self, name: str, info: Dict) -> str:
        deps = list(info.get('dependencies', set()))[:5]
        dep_lines = '\n'.join(f'    "{dep}" = "latest"' for dep in deps if dep not in ['std'])
        return f'''[package]
name = "{name}"
version = "0.1.0"
edition = "2021"

[dependencies]
{dep_lines if dep_lines else '# Añade aquí tus dependencias'}

[[bin]]
name = "{name}"
path = "src/main.rs"
'''

    def _make_go_mod(self, name: str, info: Dict) -> str:
        return f'''module {name}

go 1.21

require (
    # Añade aquí tus dependencias
)
'''

    def _make_makefile(self, name: str, language: str, main_file: Optional[str]) -> str:
        compiler = 'g++' if language == 'cpp' else 'gcc'
        standard = '-std=c++17' if language == 'cpp' else '-std=c11'
        src = os.path.basename(main_file) if main_file else f'src/main.{language}'
        return f'''# Makefile para proyecto {language.upper()}
# Generado por Compilador Profesional

{compiler.upper()} = {compiler}
CFLAGS = -Wall -Wextra -O2 {standard}
LDFLAGS =

TARGET = {name}
SRCS = {src}
OBJS = $(SRCS:.{language}=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
\t$({compiler.upper()}) $(CFLAGS) -o $@ $^ $(LDFLAGS)

%.o: %.{language}
\t$({compiler.upper()}) $(CFLAGS) -c $< -o $@

clean:
\trm -f $(OBJS) $(TARGET)

run: $(TARGET)
\t./$(TARGET)

.PHONY: all clean run
'''

    def _make_cmake(self, name: str, language: str) -> str:
        standard = '17' if language == 'cpp' else '11'
        source = "{SOURCES}"
        return f'''cmake_minimum_required(VERSION 3.10)

project({name} VERSION 0.1.0)

set(CMAKE_CXX_STANDARD {standard})
set(CMAKE_CXX_STANDARD_REQUIRED ON)

file(GLOB SOURCES "src/*.{language}")

add_executable({name} ${source})

target_include_directories({name} PRIVATE include)
'''

    def _make_pom_xml(self, name: str, info: Dict) -> str:
        group_id = os.path.basename(info.get('project_dir', 'com.example'))
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>{group_id}</groupId>
    <artifactId>{name}</artifactId>
    <version>1.0-SNAPSHOT</version>
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
    </properties>
    <dependencies>
        <!-- Añade aquí tus dependencias -->
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-jar-plugin</artifactId>
                <version>3.2.0</version>
                <configuration>
                    <archive>
                        <manifest>
                            <mainClass>{group_id}.{name}.Main</mainClass>
                        </manifest>
                    </archive>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
'''

    def _make_package_json(self, name: str, main_file: Optional[str]) -> str:
        main = os.path.basename(main_file) if main_file else 'index.js'
        return f'''{{
  "name": "{name}",
  "version": "1.0.0",
  "description": "Descripción del proyecto",
  "main": "{main}",
  "scripts": {{
    "start": "node {main}",
    "test": "echo \\"Error: no test specified\\" && exit 1"
  }},
  "dependencies": {{}},
  "devDependencies": {{}}
}}
'''

    def _make_csproj(self, name: str) -> str:
        return f'''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <RootNamespace>{name}</RootNamespace>
  </PropertyGroup>
</Project>
'''

    def _make_gitignore(self, lang: str) -> str:
        templates = {
            'python': """__pycache__/
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
""",
            'rust': """target/
Cargo.lock
*.rs.bk
""",
            'go': """*.exe
*.test
*.out
vendor/
""",
            'c': """*.o
*.obj
*.exe
*.out
*.so
*.dll
*.a
*.lib
build/
""",
            'java': """*.class
*.jar
*.war
*.ear
target/
.idea/
*.iml
""",
            'node': """node_modules/
npm-debug.log
yarn-error.log
package-lock.json
yarn.lock
.env
""",
            'dotnet': """bin/
obj/
*.user
*.suo
"""
        }
        return templates.get(lang, """# .gitignore generado por Compilador Profesional
*.log
*.tmp
.DS_Store
Thumbs.db
""")
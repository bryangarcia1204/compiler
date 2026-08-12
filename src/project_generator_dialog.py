# src/project_generator_dialog.py
"""
Diálogo para el generador de proyectos con IA.
"""

import os
import sys
from typing import Dict, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QTextEdit, QTabWidget, QCheckBox,
    QGroupBox, QFileDialog, QMessageBox, QProgressDialog,
    QWidget, QSplitter, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from .project_generator import ProjectGenerator
from .project_analyzer import ProjectAnalyzer
from .compilation_engine import CompilationEngine
from .compiler_detector import CompilerDetector
from . import logger

log = logger.Logger()


class GenerateWorker(QThread):
    """Worker para generar archivos sin bloquear la GUI."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, generator, project_info, custom_prompt):
        super().__init__()
        self.generator = generator
        self.project_info = project_info
        self.custom_prompt = custom_prompt

    def run(self):
        try:
            result = self.generator.generate_config_files(self.project_info, self.custom_prompt)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ProjectGeneratorDialog(QDialog):
    """Ventana principal del generador de proyectos."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generador de Proyectos - Compilador Profesional")
        self.setGeometry(200, 200, 1000, 700)

        self.project_dir = ""
        self.project_info = {}
        self.generated_files = {}
        self.edited_files = {}

        self.generator = ProjectGenerator(
            use_ai=False,
            api_key=None,
            api_base=None
        )

        self.analyzer:ProjectAnalyzer = None

        self.init_ui()
        self.load_config()

    def init_ui(self):
        """Inicializa la interfaz gráfica."""
        main_layout = QVBoxLayout(self)

        # ── Barra superior ──
        top_layout = QHBoxLayout()

        self.dir_label = QLabel("Directorio:")
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("Selecciona un directorio de proyecto...")
        self.dir_edit.textChanged.connect(self.on_dir_changed)


        self.browse_btn = QPushButton("Examinar...")
        self.browse_btn.clicked.connect(self.browse_directory)

        top_layout.addWidget(self.dir_label)
        top_layout.addWidget(self.dir_edit, 1)
        top_layout.addWidget(self.browse_btn)

        main_layout.addLayout(top_layout)

        # ── Panel de información ──
        info_group = QGroupBox("Información del proyecto")
        info_layout = QVBoxLayout()

        self.info_label = QLabel("Selecciona un directorio para analizar...")
        info_layout.addWidget(self.info_label)

        # Botón Analizar
        self.analyze_btn = QPushButton("Analizar proyecto")
        self.analyze_btn.clicked.connect(self.analyze_project)
        self.analyze_btn.setEnabled(False)
        info_layout.addWidget(self.analyze_btn)

        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # ── Opciones de generación ──
        options_group = QGroupBox("Opciones de generación")
        options_layout = QVBoxLayout()

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["DeepSeek", "OpenAI", "Groq", "Plataformia"])
        self.provider_combo.setCurrentText("Plataformia")
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("Modelo (ej. radiance, llama3-70b-8192)")
        self.model_edit.setText("radiance")

        # Checkbox IA
        self.ai_checkbox = QCheckBox("Usar IA para generar archivos (requiere API key)")
        self.ai_checkbox.toggled.connect(self.on_ai_toggled)
        options_layout.addWidget(self.ai_checkbox)
        options_layout.addWidget(self.provider_combo)
        options_layout.addWidget(self.model_edit)

        # API Key
        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("API Key:"))
        self.api_edit = QLineEdit()
        self.api_edit.setPlaceholderText("sk-...")
        self.api_edit.setEchoMode(QLineEdit.Password)
        self.api_edit.setEnabled(False)
        api_layout.addWidget(self.api_edit)
        options_layout.addLayout(api_layout)

        # Prompt personalizado
        options_layout.addWidget(QLabel("Prompt personalizado (opcional):"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Describe qué tipo de proyecto quieres generar...")
        self.prompt_edit.setMaximumHeight(80)
        self.prompt_edit.setEnabled(False)
        options_layout.addWidget(self.prompt_edit)

        # Botón Generar
        self.generate_btn = QPushButton("Generar archivos de configuración")
        self.generate_btn.clicked.connect(self.generate_files)
        self.generate_btn.setEnabled(False)
        options_layout.addWidget(self.generate_btn)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # ── Editor de archivos ──
        editor_group = QGroupBox("Editor de archivos")
        editor_layout = QVBoxLayout()

        self.file_tabs = QTabWidget()
        self.file_tabs.setTabsClosable(True)
        self.file_tabs.tabCloseRequested.connect(self.close_tab)
        editor_layout.addWidget(self.file_tabs)

        # Barra de acciones del editor
        editor_actions = QHBoxLayout()
        self.save_btn = QPushButton("Guardar archivos")
        self.save_btn.clicked.connect(self.save_files)
        self.save_btn.setEnabled(False)

        self.save_compile_btn = QPushButton("Guardar y compilar")
        self.save_compile_btn.clicked.connect(self.save_and_compile)
        self.save_compile_btn.setEnabled(False)

        editor_actions.addWidget(self.save_btn)
        editor_actions.addWidget(self.save_compile_btn)
        editor_actions.addStretch()
        editor_layout.addLayout(editor_actions)

        editor_group.setLayout(editor_layout)
        main_layout.addWidget(editor_group, 1)

        # ── Botones finales ──
        btn_layout = QHBoxLayout()
        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)

        main_layout.addLayout(btn_layout)

        # Configurar fuentes
        font = QFont("Consolas", 9)
        self.prompt_edit.setFont(font)

    # ──────────────────────────────────────────────────────────
    # MÉTODOS DE LA GUI
    # ──────────────────────────────────────────────────────────
    def on_provider_changed(self, provider):
        """Actualiza la URL base según el proveedor seleccionado."""

        default_models = {
            "plataformia": "radiance",
            "openai": "gpt-4o-mini",
            "groq": "llama3-70b-8192",
            "DeepSeek": "deepseek-coder"
        }
        self.model_edit.setText(default_models.get(provider, ""))

    def browse_directory(self):
        """Abre diálogo para seleccionar directorio."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar directorio del proyecto",
            self.dir_edit.text() or os.path.expanduser("~")
        )
        if dir_path:
            self.dir_edit.setText(dir_path)

    def on_dir_changed(self, text: str):
        """Actualiza el estado del botón Analizar."""
        self.analyze_btn.setEnabled(bool(text.strip()))

    def on_ai_toggled(self, checked: bool):
        """Habilita/deshabilita opciones de IA."""
        self.api_edit.setEnabled(checked)
        self.prompt_edit.setEnabled(checked)
        if checked:
            # Cargar API key de la configuración si existe
            self.api_edit.setText(self.get_saved_api_key())

    def get_saved_api_key(self) -> str:
        """Obtiene la API key guardada en la configuración."""
        # Implementar según tu sistema de configuración
        return ""

    def load_config(self):
        """Carga configuración guardada."""
        # Aquí puedes cargar la API key desde config.json
        pass

    def analyze_project(self):
        """Analiza el proyecto de forma semántica."""
        self.project_dir = self.dir_edit.text().strip()
        if not os.path.isdir(self.project_dir):
            QMessageBox.warning(self, "Error", f"El directorio '{self.project_dir}' no existe.")
            return

        self.info_label.setText("Analizando proyecto...")
        self.analyze_btn.setEnabled(False)

        # Crear analizador
        provider = self.provider_combo.currentText()
        model = self.model_edit.text().strip() or None

        self.analyzer = ProjectAnalyzer(
            self.project_dir,
            use_ai=self.ai_checkbox.isChecked(),
            provider=provider.lower(),  # <-- convertir a minúsculas
            api_key=self.api_edit.text().strip(),
            model=model
        )

        self.project_info = self.analyzer.analyze()

        # ── OBTENER DATOS CORRECTOS DEL ANÁLISIS ──
        main_language = self.project_info.get('main_language', 'Desconocido')
        project_type = self.project_info.get('project_type', 'Desconocido')
        binary_target = self.project_info.get('binary_target', 'Ninguno')

        # Archivos fuente (de source_files o files)
        source_files = self.project_info.get('source_files', [])
        if not source_files:
            source_files = self.project_info.get('files', [])

        # Archivos principales (main_files)
        main_files = self.project_info.get('main_files', [])
        main_file = main_files[0] if main_files else None

        # Dependencias
        dependencies = list(self.project_info.get('dependencies', set()))[:5]

        # Archivos de configuración
        config_files = []
        for entry in self.project_info.get('config_files', []):
            if isinstance(entry, dict):
                config_files.append(entry.get('name', ''))
            elif isinstance(entry, str):
                config_files.append(os.path.basename(entry))

        # Archivos sugeridos
        suggested = self.project_info.get('suggested_config_files', [])

        # Evidencia
        evidence = self.project_info.get('evidence', [])[:5]

        info_text = f"""
    📁 **Directorio:** {self.project_dir}
    📝 **Lenguaje principal:** {main_language}
    📄 **Tipo de proyecto:** {project_type}
    📦 **Target binario:** {binary_target}
    📂 **Archivos fuente:** {len(source_files)}
    📦 **Dependencias detectadas:** {', '.join(dependencies) or 'Ninguna'}
    📋 **Configuración existente:** {', '.join(config_files) or 'Ninguna'}
    💡 **Archivos sugeridos:** {', '.join(suggested) or 'Ninguno'}
    🎯 **Confianza:** {self.project_info.get('intent_confidence', 0) * 100:.1f}%

    🔍 **Evidencia:**
    {chr(10).join(['  • ' + e for e in evidence])}
    """

        if self.project_info.get('ai_suggestions'):
            ai = self.project_info['ai_suggestions']
            info_text += f"""
    🤖 **Sugerencias de IA:**
    - Tipo: {ai.get('project_type', 'N/A')}
    - Recomendaciones: {', '.join(ai.get('recommendations', [])[:3])}
    """

        self.info_label.setText(info_text)

        # Guardar información para uso posterior
        self.project_info['main_file'] = main_file
        self.project_info['source_files'] = source_files
        self.project_info['config_files'] = config_files
        self.project_info['needs_config_files'] = suggested
        self.project_info['language'] = main_language

        # Si se detecta que el proyecto necesita archivos, preguntar
        if suggested:
            reply = QMessageBox.question(
                self,
                "Archivos sugeridos",
                f"El proyecto necesita los siguientes archivos:\n"
                f"{', '.join(suggested)}\n\n"
                "¿Deseas generarlos ahora?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.generate_files()

        self.generate_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)

    def generate_files(self):
        """Genera los archivos de configuración."""
        if not self.project_info:
            QMessageBox.warning(self, "Error", "Primero analiza el proyecto.")
            return

        # Configurar generador
        self.generator = ProjectGenerator(
            use_ai=self.ai_checkbox.isChecked(),
            provider=self.provider_combo.currentText().lower(),
            api_key=self.api_edit.text().strip() if self.ai_checkbox.isChecked() else None,
            model=self.model_edit.text().strip() or None
        )
        

        prompt = self.prompt_edit.toPlainText().strip()

        self.generate_btn.setEnabled(False)
        self.info_label.setText("Generando archivos...")

        # Crear worker para generación asíncrona
        self.worker = GenerateWorker(self.generator, self.project_info, prompt)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)
        self.worker.start()

    def on_generation_finished(self, files: Dict[str, str]):
        """Maneja la finalización de la generación."""
        self.generated_files = files
        self.edited_files = files.copy()

        # Limpiar tabs
        for i in range(self.file_tabs.count() - 1, -1, -1):
            self.file_tabs.removeTab(i)

        # Mostrar cada archivo en un tab
        for filename, content in files.items():
            self.add_file_tab(filename, content)

        self.generate_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.save_compile_btn.setEnabled(True)

        self.info_label.setText(f"✅ Archivos generados: {len(files)}")

        if self.generator.use_ai:
            log.info(f"[ProjectGeneratorDialog] Archivos generados con IA: {list(files.keys())}")
        else:
            log.info(f"[ProjectGeneratorDialog] Archivos generados con plantillas: {list(files.keys())}")

    def on_generation_error(self, error: str):
        """Maneja errores en la generación."""
        self.generate_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Error al generar archivos:\n{error}")
        self.info_label.setText("❌ Error al generar archivos")

    def add_file_tab(self, filename: str, content: str):
        """Añade un nuevo tab con el contenido del archivo."""
        editor = QTextEdit()
        editor.setFontFamily("Consolas")
        editor.setFontPointSize(10)
        editor.setTabStopDistance(4 * 10)
        editor.setPlainText(content)
        editor.textChanged.connect(lambda: self.on_file_edited(filename, editor.toPlainText()))

        self.file_tabs.addTab(editor, filename)

    def on_file_edited(self, filename: str, content: str):
        """Marca el archivo como editado."""
        self.edited_files[filename] = content

        # Actualizar título del tab para indicar cambios
        idx = self.file_tabs.indexOf(self.file_tabs.currentWidget())
        if idx >= 0:
            current_name = self.file_tabs.tabText(idx)
            if not current_name.startswith("*"):
                self.file_tabs.setTabText(idx, f"*{current_name}")

    def close_tab(self, index: int):
        """Cierra un tab y descarta el archivo."""
        filename = self.file_tabs.tabText(index)
        reply = QMessageBox.question(
            self,
            "Cerrar archivo",
            f"¿Deseas descartar los cambios en '{filename}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.file_tabs.removeTab(index)
            # Si no quedan tabs, deshabilitar botones
            if self.file_tabs.count() == 0:
                self.save_btn.setEnabled(False)
                self.save_compile_btn.setEnabled(False)

    def save_files(self):
        """Guarda todos los archivos editados en el disco."""
        if not self.project_dir:
            QMessageBox.warning(self, "Error", "No hay directorio de proyecto.")
            return

        # Recoger todos los editores
        for i in range(self.file_tabs.count()):
            editor = self.file_tabs.widget(i)
            filename = self.file_tabs.tabText(i).lstrip("*")
            if editor and filename in self.edited_files:
                self.edited_files[filename] = editor.toPlainText()

        # Guardar archivos
        saved = 0
        for filename, content in self.edited_files.items():
            filepath = os.path.join(self.project_dir, filename)
            try:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved += 1
                # Quitar el asterisco del tab
                for i in range(self.file_tabs.count()):
                    if self.file_tabs.tabText(i).lstrip("*") == filename:
                        self.file_tabs.setTabText(i, filename)
            except Exception as e:
                log.error(f"[ProjectGeneratorDialog] Error guardando {filename}: {e}")
                QMessageBox.warning(self, "Error", f"Error guardando {filename}:\n{e}")

        QMessageBox.information(self, "Guardado", f"Se guardaron {saved} archivos.")
        log.info(f"[ProjectGeneratorDialog] Archivos guardados: {saved}")

    def _detect_output_type(self, project_type: str, language: str, binary_target: str, main_file: str) -> str:
        """
        Detecta automáticamente el tipo de salida según el proyecto.
        """
        # Si se detectó un target binario específico
        if binary_target:
            return binary_target

        # Por lenguaje
        if language == 'python':
            if project_type in ['library', 'binary_extension']:
                # Detectar si es una extensión C/C++
                if self._has_cpp_files():
                    return 'pyd'
                # Si es biblioteca pura Python
                return 'whl'
            else:
                return 'exe'  # Si no, ejecutable

        elif language == 'rust':
            if project_type == 'library':
                return 'rlib'
            return 'exe'

        elif language == 'java':
            if project_type == 'library':
                return 'jar'
            return 'jar'  # Los proyectos Java generan JAR

        elif language == 'c' or language == 'cpp':
            if project_type == 'binary_extension':
                return 'dll' if os.name == 'nt' else 'so'
            return 'exe'

        elif language == 'go':
            if project_type == 'library':
                return 'go-bin'  # No hay bibliotecas estándar en Go
            return 'exe'

        elif language == 'node':
            if project_type == 'library':
                return 'nodepkg'
            return 'nodebin'

        # Por defecto
        return 'exe'

    def _has_cpp_files(self) -> bool:
        """Verifica si el proyecto tiene archivos C/C++."""
        # Usar source_files del analizador
        source_files = self.project_info.get('source_files', [])
        for entry in source_files:
            if isinstance(entry, dict):
                lang = entry.get('language', '')
                if lang in ('c', 'cpp'):
                    return True
            elif isinstance(entry, str):
                if entry.endswith(('.cpp', '.c', '.cc', '.cxx', '.h', '.hpp')):
                    return True
        return False

    def _detect_build_command(self, project_type: str, language: str, binary_target: str, main_file: str) -> Optional[Dict]:
        """
        Detecta el comando de build apropiado para el proyecto.
        """
        # Obtener config_files del proyecto_info
        config_files = self.project_info.get('config_files', [])
        project_dir = self.project_dir

        # ── Python ──
        if language == 'python':
            if 'setup.py' in config_files and self._has_cpp_files():
                return {
                    'cmd': ['python', 'setup.py', 'build_ext', '--inplace'],
                    'cwd': project_dir,
                    'timeout': 300,
                    'description': 'Compilando extensión C++ con pybind11'
                }
            elif 'pyproject.toml' in config_files:
                if self._has_scikit_build():
                    return {
                        'cmd': ['python', '-m', 'build', '--wheel'],
                        'cwd': project_dir,
                        'timeout': 600,
                        'description': 'Compilando con scikit-build'
                    }
                else:
                    return {
                        'cmd': ['python', '-m', 'build'],
                        'cwd': project_dir,
                        'timeout': 300,
                        'description': 'Compilando con build (pyproject.toml)'
                    }
            elif 'setup.py' in config_files:
                return {
                    'cmd': ['python', 'setup.py', 'build'],
                    'cwd': project_dir,
                    'timeout': 120,
                    'description': 'Construyendo biblioteca Python'
                }
            elif main_file and main_file.endswith('.py'):
                return {
                    'cmd': ['python', main_file],
                    'cwd': project_dir,
                    'timeout': 60,
                    'description': 'Ejecutando script Python'
                }

        # ── Rust ──
        elif language == 'rust':
            if 'Cargo.toml' in config_files:
                release = '--release' if project_type == 'library' else ''
                return {
                    'cmd': ['cargo', 'build'] + ([release] if release else []),
                    'cwd': project_dir,
                    'timeout': 600,
                    'description': f'Compilando Rust con Cargo ({"release" if release else "debug"})'
                }

        # ── C/C++ ──
        elif language in ('c', 'cpp'):
            if 'CMakeLists.txt' in config_files:
                build_dir = os.path.join(project_dir, 'build')
                os.makedirs(build_dir, exist_ok=True)
                return {
                    'cmd': ['cmake', '..', '&&', 'cmake', '--build', '.'],
                    'cwd': build_dir,
                    'timeout': 600,
                    'description': 'Compilando con CMake'
                }
            elif 'Makefile' in config_files:
                return {
                    'cmd': ['make'],
                    'cwd': project_dir,
                    'timeout': 300,
                    'description': 'Compilando con Makefile'
                }
            elif main_file:
                output_ext = '.exe' if os.name == 'nt' else ''
                output_name = os.path.splitext(os.path.basename(main_file))[0] + output_ext
                compiler = 'g++' if language == 'cpp' else 'gcc'
                return {
                    'cmd': [compiler, main_file, '-o', output_name],
                    'cwd': project_dir,
                    'timeout': 120,
                    'description': f'Compilando {os.path.basename(main_file)} con {compiler}'
                }

        # ── Go ──
        elif language == 'go':
            if 'go.mod' in config_files:
                return {
                    'cmd': ['go', 'build'],
                    'cwd': project_dir,
                    'timeout': 300,
                    'description': 'Compilando Go con módulo'
                }
            elif main_file:
                return {
                    'cmd': ['go', 'build', main_file],
                    'cwd': project_dir,
                    'timeout': 120,
                    'description': f'Compilando {os.path.basename(main_file)} con Go'
                }

        # ── Java ──
        elif language == 'java':
            if 'pom.xml' in config_files:
                return {
                    'cmd': ['mvn', 'clean', 'compile', 'package'],
                    'cwd': project_dir,
                    'timeout': 600,
                    'description': 'Compilando con Maven'
                }
            elif main_file:
                return {
                    'cmd': ['javac', main_file],
                    'cwd': project_dir,
                    'timeout': 120,
                    'description': f'Compilando {os.path.basename(main_file)} con javac'
                }

        # ── Node.js ──
        elif language == 'node':
            if 'package.json' in config_files:
                return {
                    'cmd': ['npm', 'start'],
                    'cwd': project_dir,
                    'timeout': 60,
                    'description': 'Ejecutando proyecto Node.js'
                }
            elif main_file:
                return {
                    'cmd': ['node', main_file],
                    'cwd': project_dir,
                    'timeout': 60,
                    'description': f'Ejecutando {os.path.basename(main_file)} con Node.js'
                }

        return None

    def _has_scikit_build(self) -> bool:
        """Verifica si el proyecto usa scikit-build."""
        try:
            pyproject_path = os.path.join(self.project_dir, 'pyproject.toml')
            if os.path.exists(pyproject_path):
                import tomllib
                with open(pyproject_path, 'rb') as f:
                    data = tomllib.load(f)
                    build_system = data.get('build-system', {})
                    requires = build_system.get('requires', [])
                    return any('scikit-build' in r for r in requires)
        except Exception:
            pass
        return False

    def _run_build_command(self, build_info: Dict) -> Dict:
        """
        Ejecuta un comando de build y devuelve el resultado.
        """
        import subprocess

        cmd = build_info['cmd']
        cwd = build_info.get('cwd', self.project_dir)
        timeout = build_info.get('timeout', 300)

        log.info(f"[ProjectGeneratorDialog] {build_info['description']}")
        log.debug(f"[ProjectGeneratorDialog] Comando: {' '.join(cmd)}")

        try:
            # Si es un comando compuesto (con &&)
            if len(cmd) > 1 and '&&' in cmd:
                cmd_str = ' '.join(cmd)
                result = subprocess.run(
                    cmd_str,
                    shell=True,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            else:
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

            # Determinar el archivo de salida
            output_file = self._find_output_file(build_info)

            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'output_file': output_file
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Tiempo de ejecución excedido ({timeout}s)',
                'returncode': -1,
                'output_file': None
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1,
                'output_file': None
            }

    def _find_output_file(self, build_info: Dict) -> Optional[str]:
        """
        Intenta encontrar el archivo de salida generado por la compilación.
        """
        project_dir = self.project_dir
        output_extensions = {
            'exe': '.exe',
            'pyd': '.pyd',
            'so': '.so',
            'dll': '.dll',
            'jar': '.jar',
            'whl': '.whl',
            'rlib': '.rlib'
        }

        # Buscar archivos modificados recientemente en los directorios comunes
        search_dirs = [
            project_dir,
            os.path.join(project_dir, 'dist'),
            os.path.join(project_dir, 'target'),
            os.path.join(project_dir, 'build'),
            os.path.join(project_dir, 'src')
        ]

        latest_file = None
        latest_time = 0

        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    # Verificar extensiones comunes de archivos de salida
                    for ext in output_extensions.values():
                        if file.endswith(ext):
                            mtime = os.path.getmtime(filepath)
                            if mtime > latest_time:
                                latest_time = mtime
                                latest_file = filepath

        return latest_file

    def _compile_with_engine(self, main_file: str, output_type: str) -> Dict:
        """
        Método fallback: compila usando CompilationEngine.
        """
        detector = CompilerDetector()
        tool = detector.get_tool_for_file(main_file)

        if not tool:
            return {
                'success': False,
                'stdout': '',
                'stderr': f'No se encontró herramienta para {os.path.basename(main_file)}',
                'returncode': -1,
                'output_file': None
            }

        engine = CompilationEngine()
        output_dir = os.path.join(self.project_dir, 'dist')
        os.makedirs(output_dir, exist_ok=True)

        # Determinar extensión de salida
        ext_map = {
            'exe': '.exe' if os.name == 'nt' else '',
            'pyd': '.pyd' if os.name == 'nt' else '.so',
            'dll': '.dll',
            'so': '.so',
            'jar': '.jar',
            'whl': '.whl'
        }
        ext = ext_map.get(output_type, '.bin')
        output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(main_file))[0] + ext)

        result = engine.compile(
            file_path=main_file,
            tool=tool,
            output_path=output_file,
            extra_args=[],
            output_type=output_type,
            release_mode=False
        )

        return result

    def _show_post_compile_options(self, result: Dict):
        """Muestra opciones adicionales después de la compilación."""
        output_file = result.get('output_file')

        if not output_file or not os.path.exists(output_file):
            return

        reply = QMessageBox.question(
            self,
            "Compilación exitosa",
            f"Archivo generado: {output_file}\n\n"
            "¿Deseas ejecutarlo?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                import subprocess
                subprocess.Popen([output_file], shell=True)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo ejecutar el archivo:\n{e}")

    def save_and_compile(self):
        """Guarda archivos y compila el proyecto según el tipo detectado."""
        self.save_files()

        # ── 1. Obtener información del proyecto ──
        project_type = self.project_info.get('project_type', 'application')
        language = self.project_info.get('main_language', '')
        binary_target = self.project_info.get('binary_target')
        main_file = self.project_info.get('main_file')  # <-- ya guardado en analyze_project

        # Si main_file es una lista, tomar el primero
        if isinstance(main_file, list) and main_file:
            main_file = main_file[0]

        # ── 2. Detectar automáticamente el tipo de salida ──
        output_type = self._detect_output_type(project_type, language, binary_target, main_file)

        # ── 3. Detectar el comando de build ──
        build_command = self._detect_build_command(project_type, language, binary_target, main_file)

        if build_command:
            result = self._run_build_command(build_command)
        else:
            # Fallback con CompilationEngine
            result = self._compile_with_engine(main_file, output_type)

        # ── 4. Mostrar resultado ──
        if result['success']:
            QMessageBox.information(
                self,
                "Compilación exitosa",
                f"✅ Archivo generado:\n{result.get('output_file', 'No especificado')}"
            )
            log.info(f"[ProjectGeneratorDialog] Compilación exitosa: {result.get('output_file')}")
        else:
            QMessageBox.critical(
                self,
                "Error de compilación",
                f"❌ Error:\n{result.get('stderr', 'Error desconocido')}"
            )
            log.error(f"[ProjectGeneratorDialog] Compilación falló: {result.get('stderr')}")

        if result['success']:
            self._show_post_compile_options(result)
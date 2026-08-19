# src/project_generator_dialog.py
"""
Diálogo para el generador de proyectos con IA.
Flujo completo: persistencia, análisis con IA, generación y compilación.
"""

import os
import sys
import json
from typing import Dict, Optional, Any

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QTextEdit, QTabWidget, QCheckBox,
    QGroupBox, QFileDialog, QMessageBox, QWidget,
    QScrollArea, QMainWindow, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from .editor.editor_widget import CodeEditor
from PyQt5.QtGui import QFont

from .project_generator import ProjectGenerator
from .project_analyzer import ProjectAnalyzer
from ..compilation_engine import CompilationEngine
from ..compiler_detector import CompilerDetector
from ..config_manager import load_project_state, save_project_state
from .output_types_analyzer import OUTPUT_TYPE_MAP_ANALIZER
from ..target_manager import TargetManager
from .. import logger

log = logger.Logger()


class GenerateWorker(QThread):
    """Worker para generar archivos sin bloquear la GUI."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, generator, project_info, custom_prompt, selected_targets):
        super().__init__()
        self.generator = generator
        self.project_info = project_info
        self.custom_prompt = custom_prompt
        self.selected_targets = selected_targets or ['native']

    def run(self):
        try:
            result = self.generator.generate_config_files(self.project_info, self.custom_prompt, self.selected_targets)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class EnhanceWorker(QThread):
    """Worker para mejorar archivos con IA."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, generator, project_info, existing_files, custom_prompt):
        super().__init__()
        self.generator = generator
        self.project_info = project_info
        self.existing_files = existing_files
        self.custom_prompt = custom_prompt

    def run(self):
        try:
            result = self.generator.enhance_files_with_ai(
                self.project_info,
                self.existing_files,
                self.custom_prompt
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ProjectGeneratorDialog(QMainWindow):
    """Ventana principal del generador de proyectos con flujo completo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generador de Proyectos - Compilador Profesional")
        self.setGeometry(200, 200, 1100, 750)

        # Estado del proyecto
        self.project_dir = ""
        self.project_info = {}
        self.generated_files = {}
        self.edited_files = {}
        self.build_command = None
        self.build_description = ""
        self.has_ai_veredict = False

        # Crear analizador y generador
        self.analyzer = None
        self.generator = ProjectGenerator(use_ai=False)

        # Inicializar UI
        self.init_ui()
        # Después de self.init_ui(), agregar:
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #f0f0f0;
            }
            QLabel {
                color: #f0f0f0;
                background-color: transparent;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: #f0f0f0;
                border: 1px solid #5a5a5a;
                border-radius: 3px;
                padding: 4px;
            }
            QPushButton {
                background-color: #3c3c3c;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 6px 12px;
                color: #f0f0f0;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #6a6a6a;
            }
        """)
        self.load_config()

    def init_ui(self):
        """Inicializa la interfaz gráfica."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        self.setCentralWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        main_layout = QVBoxLayout(container)

        # ── BARRA SUPERIOR ──
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

        # ── PANEL DE INFORMACIÓN ──
        info_group = QGroupBox("Información del proyecto")
        info_layout = QVBoxLayout()

        self.info_label = QLabel("Selecciona un directorio para analizar...")
        self.info_label.setWordWrap(True)
        self.info_label.setMinimumHeight(100)
        info_layout.addWidget(self.info_label)

        # Botón Analizar
        self.analyze_btn = QPushButton("Analizar proyecto")
        self.analyze_btn.clicked.connect(self.analyze_project)
        self.analyze_btn.setEnabled(False)
        info_layout.addWidget(self.analyze_btn)

        self.build_all_btn = QPushButton("Construir todo (multi-lenguaje)")
        self.build_all_btn.clicked.connect(self.build_all_projects)
        self.build_all_btn.setEnabled(False)
        info_layout.addWidget(self.build_all_btn)

        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        self.target_list = QListWidget()
        self.target_list.setSelectionMode(QListWidget.MultiSelection)
        available_targets = TargetManager.get_available_targets()
        for t in available_targets:
            item = QListWidgetItem(t)
            item.setToolTip(TargetManager.get_target(t).description)
            self.target_list.addItem(item)
        # Seleccionar 'native' por defecto
        for i in range(self.target_list.count()):
            if self.target_list.item(i).text() == 'native':
                self.target_list.item(i).setSelected(True)
        target_layout = QHBoxLayout()
        target_layout.addWidget(self.target_list)

        # ── OPCIONES DE GENERACIÓN ──
        options_group = QGroupBox("Opciones de generación")
        options_layout = QVBoxLayout()

        # Checkbox IA
        self.ai_checkbox = QCheckBox("Usar IA para generar/mejorar archivos")
        self.ai_checkbox.toggled.connect(self.on_ai_toggled)
        options_layout.addWidget(self.ai_checkbox)

        # Proveedor y modelo
        provider_layout = QHBoxLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Plataformia", "DeepSeek", "OpenAI", "Groq", "HuggingFace", "Qwen-Code"])
        self.provider_combo.setCurrentText("Plataformia")
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(QLabel("Proveedor:"))
        provider_layout.addWidget(self.provider_combo)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("Modelo (ej. radiance, deepseek-coder)")
        self.model_edit.setText("agent-xs")
        provider_layout.addWidget(QLabel("Modelo:"))
        provider_layout.addWidget(self.model_edit, 1)
        options_layout.addLayout(provider_layout)

        # API Key
        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("API Key:"))
        self.api_edit = QLineEdit()
        self.api_edit.setPlaceholderText("sk-...")
        self.api_edit.setEchoMode(QLineEdit.Password)
        self.api_edit.setEnabled(False)
        api_layout.addWidget(self.api_edit, 1)
        options_layout.addLayout(api_layout)

        options_layout.addLayout(target_layout)
        

        # Prompt personalizado
        options_layout.addWidget(QLabel("Prompt personalizado (opcional):"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Describe qué tipo de proyecto quieres generar o qué mejoras quieres...")
        self.prompt_edit.setMaximumHeight(60)
        self.prompt_edit.setEnabled(False)
        options_layout.addWidget(self.prompt_edit)
        

        # Botones de acción
        action_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Generar archivos de configuración")
        self.generate_btn.clicked.connect(self.generate_files)
        self.generate_btn.setEnabled(False)
        action_layout.addWidget(self.generate_btn)

        self.enhance_btn = QPushButton("Mejorar con IA")
        self.enhance_btn.clicked.connect(self.enhance_files_with_ai)
        self.enhance_btn.setEnabled(False)
        action_layout.addWidget(self.enhance_btn)

        options_layout.addLayout(action_layout)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # ── EDITOR DE ARCHIVOS ──
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

        # ── BOTONES FINALES ──
        btn_layout = QHBoxLayout()
        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.close)
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
        """Actualiza el modelo por defecto según el proveedor."""
        default_models = {
            "Plataformia": "agent-xs",
            "DeepSeek": "deepseek-coder",
            "OpenAI": "gpt-4o-mini",
            "Groq": "llama3-70b-8192",
            "HuggingFace": "deepseek-ai/DeepSeek-V4-Pro-0813:fireworks-ai",
            "Qwen-Code": "qwen2.5-coder-1.5b-instruct-q3_k_m.gguf"
        }
        self.model_edit.setText(default_models.get(provider, ""))

        # Si es TinyLlama, mostrar un mensaje sobre la ruta del modelo
        if provider == "TinyLlama":
            self.api_edit.setPlaceholderText("No se requiere API key")
            self.api_edit.setEnabled(False)
            self.api_edit.setEchoMode(QLineEdit.Normal)
            self.api_edit.setText("MODELO LOCAL")

    def on_ai_toggled(self, checked):
        """Habilita/deshabilita opciones de IA."""
        self.api_edit.setEnabled(checked)
        self.prompt_edit.setEnabled(checked)

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

    def load_config(self):
        """Carga el estado guardado del proyecto."""
        state = load_project_state()
        if state:
            project_dir = state.get('project_dir')
            if project_dir and os.path.isdir(project_dir):
                reply = QMessageBox.question(
                    self,
                    "Cargar proyecto",
                    f"Se encontró un proyecto guardado en:\n{project_dir}\n\n¿Deseas cargarlo?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.dir_edit.setText(project_dir)
                    self.project_info = state.get('summary', {})
                    self.generated_files = state.get('generated_files', {})
                    self.edited_files = state.get('edited_files', {})
                    self.build_command = state.get('build_command')
                    self.build_description = state.get('build_description', '')

                    # Restaurar pestañas
                    if self.generated_files:
                        for name, content in self.generated_files.items():
                            self.add_file_tab(name, content)
                        self.save_btn.setEnabled(True)
                        self.save_compile_btn.setEnabled(True)

                    # Mostrar información
                    self._update_info_label()
                    QTimer.singleShot(100, lambda: self.info_label.setText(self.analyzer.get_summary() if self.analyzer else "Proyecto cargado"))
                    self.generate_btn.setEnabled(True)
                    self.enhance_btn.setEnabled(True)

    def build_all_projects(self):
        """Ejecuta el pipeline de construcción multi-lenguaje."""
        from ..build_orchestrator import BuildOrchestrator

        # Guardar archivos primero
        self.save_files()

        # Crear orquestador
        orchestrator = BuildOrchestrator(self.project_dir)
        orchestrator.create_pipeline(self.project_info)

        self.build_all_btn.setEnabled(False)
        self.info_label.setText("Construyendo todo el proyecto...")

        try:
            if orchestrator.run():
                QMessageBox.information(self, "Éxito", "Proyecto construido correctamente.")
            else:
                QMessageBox.critical(self, "Error", "Falló la construcción.")
        finally:
            self.build_all_btn.setEnabled(True)
            self.info_label.setText("Listo")

    # ──────────────────────────────────────────────────────────
    # 1. ANÁLISIS DEL PROYECTO
    # ──────────────────────────────────────────────────────────

    def analyze_project(self):
        """Analiza el proyecto de forma semántica."""
        self.project_dir = self.dir_edit.text().strip()
        if not os.path.isdir(self.project_dir):
            QMessageBox.warning(self, "Error", f"El directorio '{self.project_dir}' no existe.")
            return

        self.info_label.setText("Analizando proyecto...")
        self.analyze_btn.setEnabled(False)

        # Crear analizador
        provider = self.provider_combo.currentText().lower()
        model = self.model_edit.text().strip() or None
        api_key = self.api_edit.text().strip() if self.ai_checkbox.isChecked() else None

        self.analyzer = ProjectAnalyzer(
            self.project_dir,
            use_ai=self.ai_checkbox.isChecked(),
            provider=provider,
            api_key=api_key,
            model=model
        )

        # Ejecutar análisis (esto crea/actualiza .compilador automáticamente)
        self.project_info = self.analyzer.analyze()

        # ── CARGAR/CREAR .compilador ──
        from ..compilador_config import CompiladorConfig
        self.compilador = CompiladorConfig(self.project_dir, auto_create=True)

        

        # ── SI IA ACTIVA: OBTENER VEREDICTO ──
        if self.ai_checkbox.isChecked() and self.analyzer.ai_client:
            self.info_label.setText("Obteniendo veredicto de IA...")
            veredict = self.analyzer.get_ai_veredict(self.prompt_edit.toPlainText().strip())
            if veredict:
                self.project_info.update(veredict)
                self.project_info['ai_veredict'] = veredict
                self.has_ai_veredict = True
                self.info_label.setText("✅ Veredicto de IA obtenido y aplicado.")
                # Actualizar .compilador con el veredicto
                self.compilador.set('project.type', veredict.get('project_type', self.project_info['project_type']))
                self.compilador.save()
            else:
                self.info_label.setText("⚠️ No se pudo obtener veredicto de IA. Usando análisis estándar.")

        # ── MOSTRAR INFORMACIÓN ──
        self._update_info_label()

        # ── GUARDAR ESTADO ──
        self._save_state()

        # Abrir .compilador en el editor
        self._open_config_in_editor()
        
        # ── PREGUNTAR SI GENERAR ARCHIVOS ──
        # Ahora .compilador ya existe, lo usamos para decidir qué hacer
        targets = self.compilador.get('targets', [])
        if not targets:
            reply = QMessageBox.question(
                self,
                "Configuración del proyecto",
                "No hay targets definidos en .compilador.\n"
                "¿Deseas crear uno por defecto?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.generate_files()

        self.build_all_btn.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.enhance_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)

    def _open_config_in_editor(self):
        """Abre el archivo .compilador en el editor"""
        if not hasattr(self, 'compilador') or not self.compilador:
            return

        config_path = str(self.compilador.config_path)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.add_file_tab('.compilador', content)
                self.save_btn.setEnabled(True)
                self.save_compile_btn.setEnabled(True)
            except Exception as e:
                log.error(f"[ProjectGeneratorDialog] Error abriendo .compilador: {e}")

    def _update_info_label(self):
        """Actualiza la etiqueta de información."""
        if self.analyzer:
            summary = self.analyzer.get_summary()
            if self.project_info.get('ai_veredict'):
                summary += "\n\n🤖 **Veredicto de IA aplicado.**"
            self.info_label.setText(summary)
        else:
            self.info_label.setText("Proyecto analizado. Usa el generador para crear archivos.")

    # ──────────────────────────────────────────────────────────
    # 2. GENERACIÓN DE ARCHIVOS
    # ──────────────────────────────────────────────────────────

    def generate_files(self):
        """Genera los archivos de configuración."""
        if not self.project_info:
            QMessageBox.warning(self, "Error", "Primero analiza el proyecto.")
            return


        selected_targets = [item.text() for item in self.target_list.selectedItems()]
        # Configurar generador
        self.generator = ProjectGenerator(
            use_ai=self.ai_checkbox.isChecked(),
            provider=self.provider_combo.currentText().lower(),
            api_key=self.api_edit.text().strip() if self.ai_checkbox.isChecked() else None,
            model=self.model_edit.text().strip() or None
        )

        prompt = self.prompt_edit.toPlainText().strip()

        self.generate_btn.setEnabled(False)
        self.enhance_btn.setEnabled(False)
        self.info_label.setText("Generando archivos...")

        # Crear worker
        self.worker = GenerateWorker(self.generator, self.project_info, prompt, selected_targets)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)
        self.worker.start()

    def on_generation_finished(self, files: Dict[str, str]):
        """Maneja la finalización de la generación."""

        config_files = self.project_info.get("config_files")
        name_config = [cf["name"] for cf in config_files]

        self.generated_files = {k:v for k,v in files.items() if k not in name_config}
        self.edited_files = self.generated_files.copy()

        # Limpiar tabs
        for i in range(self.file_tabs.count() - 1, -1, -1):
            self.file_tabs.removeTab(i)

        # Mostrar archivos
        for filename, content in files.items():
            self.add_file_tab(filename, content)

        self.generate_btn.setEnabled(True)
        self.enhance_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.save_compile_btn.setEnabled(True)

        self.info_label.setText(f"✅ Archivos generados: {len(files)}")
        self._save_state()

    def on_generation_error(self, error: str):
        """Maneja errores en la generación."""
        self.generate_btn.setEnabled(True)
        self.enhance_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Error al generar archivos:\n{error}")
        self.info_label.setText("❌ Error al generar archivos")

    # ──────────────────────────────────────────────────────────
    # 3. MEJORA DE ARCHIVOS CON IA
    # ──────────────────────────────────────────────────────────

    def enhance_files_with_ai(self):
        """Mejora los archivos de configuración con IA."""
        if not self.generated_files:
            QMessageBox.warning(self, "Error", "Primero genera los archivos o abre un proyecto.")
            return

        if not self.ai_checkbox.isChecked():
            QMessageBox.warning(self, "Error", "Activa el modo IA para usar esta función.")
            return

        # Recolectar archivos actuales
        current_files = {}
        for i in range(self.file_tabs.count()):
            editor = self.file_tabs.widget(i)
            filename = self.file_tabs.tabText(i).lstrip("*")
            if editor:
                current_files[filename] = editor.get_text().strip()

        prompt = self.prompt_edit.toPlainText().strip()

        self.enhance_btn.setEnabled(False)
        self.generate_btn.setEnabled(False)
        self.info_label.setText("Mejorando archivos con IA...")

        self.generator = ProjectGenerator(
                    use_ai=self.ai_checkbox.isChecked(),
                    provider=self.provider_combo.currentText().lower(),
                    api_key=self.api_edit.text().strip() if self.ai_checkbox.isChecked() else None,
                    model=self.model_edit.text().strip() or None
                )
        # Crear worker
        self.enhance_worker = EnhanceWorker(
            self.generator,
            self.project_info,
            current_files,
            prompt
        )
        self.enhance_worker.finished.connect(self.on_enhance_finished)
        self.enhance_worker.error.connect(self.on_enhance_error)
        self.enhance_worker.start()

    def on_enhance_finished(self, result: Dict):
        """Maneja la finalización de la mejora."""
        files = result.get('files', {})
        build_cmd = result.get('build_command')

        self.generated_files = files
        self.edited_files = files.copy()
        self.build_command = build_cmd
        if build_cmd:
            self.build_description = build_cmd.get('description', 'Comando de build')

        # Actualizar tabs
        for i in range(self.file_tabs.count() - 1, -1, -1):
            self.file_tabs.removeTab(i)

        for filename, content in files.items():
            self.add_file_tab(filename, content)

        self.enhance_btn.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.save_compile_btn.setEnabled(True)

        info = f"✅ Archivos mejorados: {len(files)}"
        if self.build_command:
            info += f" | Comando de build: {self.build_description}"
        self.info_label.setText(info)

        self._save_state()

    def on_enhance_error(self, error: str):
        """Maneja errores en la mejora."""
        self.enhance_btn.setEnabled(True)
        self.generate_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Error al mejorar archivos:\n{error}")
        self.info_label.setText("❌ Error al mejorar archivos")

    # ──────────────────────────────────────────────────────────
    # 4. EDITOR DE ARCHIVOS
    # ──────────────────────────────────────────────────────────

    def add_file_tab(self, filename: str, content: str):
        """Añade un nuevo tab con el contenido del archivo usando CodeEditor."""
        editor = CodeEditor(self, filename, content)
        editor.textChanged.connect(lambda: self.on_file_edited(filename, editor.get_text()))

        self.file_tabs.addTab(editor, filename)

    def on_file_edited(self, filename: str, content: str):
        """Marca el archivo como editado."""
        self.edited_files[filename] = content

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
                self.edited_files[filename] = editor.get_text()

        # Guardar archivos
        saved = 0
        for filename, content in self.edited_files.items():
            filepath = os.path.join(self.project_dir, filename)
            try:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved += 1
                # Quitar asterisco
                for i in range(self.file_tabs.count()):
                    if self.file_tabs.tabText(i).lstrip("*") == filename:
                        self.file_tabs.setTabText(i, filename)
            except Exception as e:
                log.error(f"[ProjectGeneratorDialog] Error guardando {filename}: {e}")
                QMessageBox.warning(self, "Error", f"Error guardando {filename}:\n{e}")

        QMessageBox.information(self, "Guardado", f"Se guardaron {saved} archivos.")
        log.info(f"[ProjectGeneratorDialog] Archivos guardados: {saved}")
        self._save_state()

    # ──────────────────────────────────────────────────────────
    # 5. COMPILACIÓN
    # ──────────────────────────────────────────────────────────

    def save_and_compile(self):
        """Guarda archivos y compila el proyecto según el tipo detectado."""
        # Guardar archivos
        self.save_files()

        # Obtener información
        project_type = self.project_info.get('project_type', 'application')
        language = self.project_info.get('main_language', '')
        binary_target = self.project_info.get('binary_target')
        main_file = self.project_info.get('main_files')

        if isinstance(main_file, list) and main_file:
            main_file = main_file[0]

        # ── 1. DETECTAR COMANDO DE BUILD ──
        build_command = self._detect_build_command(project_type, language, binary_target, main_file)

        # Si no se detectó, usar el que vino de IA
        if not build_command and self.build_command:
            build_command = self.build_command

        if build_command:
            cmd_str = ' '.join(build_command.get('cmd', []))
            reply = QMessageBox.question(
                self,
                "Confirmar compilación",
                f"Se ejecutará:\n{cmd_str}\n\n"
                f"Descripción: {build_command.get('description', 'Comando de build')}\n\n"
                "¿Usar este comando?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if reply == QMessageBox.Cancel:
                return

            if reply == QMessageBox.No:
                # Editar comando
                cmd_str = self._edit_command_dialog(cmd_str)
                if cmd_str:
                    build_command['cmd'] = cmd_str.split()
                else:
                    return

            # Ejecutar compilación
            result = self._run_build_command(build_command)

        else:
            # Fallback: CompilationEngine
            output_type = self._detect_output_type(project_type, language, binary_target, main_file)
            result = self._compile_with_engine(main_file, output_type)

        # ── 4. Mostrar resultado ──
        if result.get('success'):
            QMessageBox.information(
                self,
                "Compilación exitosa",
                f"✅ Archivo generado:\n{result.get('output_file', 'No especificado')}"
            )
            log.info(f"[ProjectGeneratorDialog] Compilación exitosa: {result.get('output_file')}")
            self._show_post_compile_options(result)
        else:
            QMessageBox.critical(
                self,
                "Error de compilación",
                f"❌ Error:\n{result.get('stderr', 'Error desconocido')}"
            )
            log.error(f"[ProjectGeneratorDialog] Compilación falló: {result.get('stderr')}")

    def _edit_command_dialog(self, current_cmd: str) -> str:
        """Abre un diálogo para editar el comando."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Editar comando de compilación")
        dialog.resize(600, 100)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Modifica el comando según necesites:"))

        cmd_edit = QLineEdit(current_cmd)
        cmd_edit.setFont(QFont("Consolas", 10))
        layout.addWidget(cmd_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Aceptar")
        cancel_btn = QPushButton("Cancelar")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        if dialog.exec_():
            return cmd_edit.text()
        return ""

    def _detect_output_type(self, project_type: str, language: str, binary_target: str, main_file: str) -> str:
        """Detecta automáticamente el tipo de salida según el proyecto."""
        if binary_target:
            return binary_target

        if language == 'python':
            if project_type in ['library', 'binary_extension']:
                if self._has_cpp_files():
                    return 'pyd'
                return 'whl'
            return 'exe'

        elif language == 'rust':
            return 'rlib' if project_type == 'library' else 'exe'

        elif language in ['c', 'cpp']:
            if project_type == 'binary_extension':
                return 'dll' if os.name == 'nt' else 'so'
            return 'exe'

        elif language == 'go':
            return 'go-bin' if project_type == 'library' else 'exe'

        elif language == 'node':
            return 'nodepkg' if project_type == 'library' else 'nodebin'

        return 'exe'

    def _has_cpp_files(self) -> bool:
        """Verifica si el proyecto tiene archivos C/C++."""
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
        """Detecta el comando de build apropiado para el proyecto."""
        config_files = self.project_info.get('config_files', [])
        project_dir = self.project_dir

        # ── Python ──
        if language == 'python':
            config_names = [e.get('name', '') if isinstance(e, dict) else e for e in config_files]
            if 'setup.py' in config_names and self._has_cpp_files():
                return {
                    'cmd': ['python', 'setup.py', 'build_ext', '--inplace'],
                    'cwd': project_dir,
                    'timeout': 300,
                    'description': 'Compilando extensión C++ con pybind11'
                }
            elif 'pyproject.toml' in config_names:
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
            elif 'setup.py' in config_names:
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
                    'description': f'Ejecutando {os.path.basename(main_file)}'
                }

        # ── Rust ──
        elif language == 'rust':
            if 'Cargo.toml' in [e.get('name', '') if isinstance(e, dict) else e for e in config_files]:
                return {
                    'cmd': ['cargo', 'build'],
                    'cwd': project_dir,
                    'timeout': 600,
                    'description': 'Compilando Rust con Cargo'
                }

        # ── C/C++ ──
        elif language in ('c', 'cpp'):
            config_names = [e.get('name', '') if isinstance(e, dict) else e for e in config_files]

            if 'CMakeLists.txt' in config_names:
                build_dir = os.path.join(project_dir, 'build')
                os.makedirs(build_dir, exist_ok=True)
                return {
                    'cmd': ['cmake', '-S', build_dir, '-B', build_dir, '&&', 'cmake', '--build', '.'],
                    'cwd': build_dir,
                    'timeout': 600,
                    'description': 'Compilando con CMake'
                }
            elif 'Makefile' in config_names:
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
            if 'go.mod' in [e.get('name', '') if isinstance(e, dict) else e for e in config_files]:
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
            if 'pom.xml' in [e.get('name', '') if isinstance(e, dict) else e for e in config_files]:
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
            if 'package.json' in [e.get('name', '') if isinstance(e, dict) else e for e in config_files]:
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
        """Ejecuta un comando de build y devuelve el resultado."""
        import subprocess

        cmd = build_info.get('cmd', [])
        cwd = build_info.get('cwd', self.project_dir)
        timeout = build_info.get('timeout', 300)

        if not cmd:
            return {'success': False, 'stderr': 'No se especificó comando', 'returncode': -1}

        log.info(f"[ProjectGeneratorDialog] {build_info.get('description', 'Ejecutando build')}")
        log.debug(f"[ProjectGeneratorDialog] Comando: {' '.join(cmd)}")

        try:
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
        """Intenta encontrar el archivo de salida generado."""
        project_dir = self.project_dir
        search_dirs = [
            project_dir,
            os.path.join(project_dir, 'dist'),
            os.path.join(project_dir, 'target'),
            os.path.join(project_dir, 'build'),
            os.path.join(project_dir, 'src'),
            os.path.join(project_dir, 'release')
        ]

        latest_file = None
        latest_time = 0
        output_exts = list(OUTPUT_TYPE_MAP_ANALIZER.keys())

        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    for ext in output_exts:
                        if file.endswith(ext):
                            mtime = os.path.getmtime(filepath)
                            if mtime > latest_time:
                                latest_time = mtime
                                latest_file = filepath

        return latest_file

    def _compile_with_engine(self, main_file: str, output_type: str) -> Dict:
        """Método fallback: compila usando CompilationEngine."""
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

        ext_map = {
            'exe': '.exe' if os.name == 'nt' else '',
            'pyd': '.pyd' if os.name == 'nt' else '.so',
            'dll': '.dll',
            'so': '.so',
            'jar': '.jar',
            'whl': '.whl',
            'rlib': '.rlib',
            'go-bin': '.go-bin',
            'nodebin': '.nodebin',
            'nodepkg': '.nodepkg'
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
                if os.name == 'nt':
                    subprocess.Popen([output_file], shell=True)
                else:
                    subprocess.Popen([output_file])
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo ejecutar el archivo:\n{e}")

    # ──────────────────────────────────────────────────────────
    # 6. PERSISTENCIA
    # ──────────────────────────────────────────────────────────

    def _save_state(self):
        """Guarda el estado actual del proyecto."""
        if not self.project_dir:
            return

        state = {
            'project_dir': self.project_dir,
            'summary': self.project_info,
            'generated_files': self.generated_files,
            'edited_files': self.edited_files,
            'build_command': self.build_command,
            'build_description': self.build_description,
        }
        save_project_state(state)

    def closeEvent(self, event):
        """Guarda el estado al cerrar."""
        self._save_state()
        event.accept()
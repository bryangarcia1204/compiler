#!/usr/bin/env python3
import sys
import os
import subprocess
import threading
import pathlib
import platform
from . import logger as logger
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QComboBox,
                             QTextEdit, QFileDialog, QMessageBox, QLineEdit,
                             QGroupBox, QRadioButton, QButtonGroup, QScrollArea,
                             QCheckBox, QDialog, QListWidget, QListWidgetItem, QStyle)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon

from .argument_suggester import ArgumentSuggester
from .language_detector import LanguageDetector
from .compiler_detector import CompilerDetector
from .compilation_engine import CompilationEngine
from .error_parser import ErrorParser
from .output_types import OUTPUT_TYPE_MAP
from .config_manager import load_config, save_config
from dotenv import load_dotenv

load_dotenv()

log = logger.Logger()

# Configuración multiplataforma
if platform.system() == 'Windows':
    CONFIG_PATH = pathlib.Path(os.environ.get('APPDATA', '')) / 'compilador' / 'config.json'
else:
    CONFIG_PATH = pathlib.Path.home() / '.config' / 'compilador' / 'config.json'

# ========== ESTILOS ==========
STYLE = """
QWidget {
    background-color: #2b2b2b;
    color: #f0f0f0;
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    margin-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}
QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #5a5a5a;
    border-radius: 4px;
    padding: 6px 12px;
    min-width: 80px;
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
QComboBox, QLineEdit, QTextEdit {
    background-color: #3c3c3c;
    border: 1px solid #5a5a5a;
    border-radius: 3px;
    padding: 4px;
    selection-background-color: #1e90ff;
}
QScrollArea {
    border: none;
}
QTextEdit {
    font-family: "Consolas", "Courier New", monospace;
    background-color: #1e1e1e;
    color: #d4d4d4;
}
QLabel {
    color: #d0d0d0;
}
QRadioButton {
    spacing: 8px;
}
QCheckBox {
    spacing: 8px;
}
"""

# ========== WORKER ==========
class CompileWorker(QThread):
    line_stdout = pyqtSignal(str)
    line_stderr = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, engine, file_path, tool, output_path, extra_args, output_type, release_mode=False):
        super().__init__()
        self.engine = engine
        self.file_path = file_path
        self.tool = tool
        self.output_path = output_path
        self.extra_args = extra_args or []
        self.output_type = output_type
        self.action = 'compile'
        self._process = None
        self._stdout_buffer = []
        self._stderr_buffer = []
        self.release_mode = release_mode

    def run(self):
        try:
            if self.action == 'compile':
                cmd, cwd, post_actions = self.engine.build_compile_command(
                    self.file_path, self.tool, self.output_path,
                    self.extra_args, self.output_type, self.release_mode
                )
            elif self.action == 'package':
                cmd, cwd, post_actions = self.engine.build_package_command(
                    self.file_path, self.tool, self.output_path, self.extra_args
                )
            else:
                self.finished.emit({'success': False, 'stdout': '', 'stderr': 'Acción no válida', 'returncode': -1, 'output_file': None})
                return

            if not cmd:
                self.finished.emit({'success': False, 'stdout': '', 'stderr': 'No se pudo construir el comando.', 'returncode': -1, 'output_file': None})
                return

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=cwd
            )

            def read_stream(stream, signal_emit, buffer_list):
                try:
                    for line in iter(stream.readline, ''):
                        if line == '':
                            break
                        cleaned = line.rstrip('\n')
                        buffer_list.append(cleaned)
                        signal_emit.emit(cleaned)
                    stream.close()
                except Exception as e:
                    buffer_list.append(f"Error leyendo stream: {e}")
                    signal_emit.emit(f"Error leyendo stream: {e}")

            t_out = threading.Thread(target=read_stream, args=(self._process.stdout, self.line_stdout, self._stdout_buffer), daemon=True)
            t_err = threading.Thread(target=read_stream, args=(self._process.stderr, self.line_stderr, self._stderr_buffer), daemon=True)
            t_out.start()
            t_err.start()

            returncode = self._process.wait()
            t_out.join(timeout=1)
            t_err.join(timeout=1)

            stdout_text = "\n".join(self._stdout_buffer)
            stderr_text = "\n".join(self._stderr_buffer)

            output_file = self.output_path
            if returncode == 0 and post_actions:
                self.engine._perform_post_actions(post_actions, cwd=cwd)
                for a in post_actions:
                    if a[0] in ('cargo_move', 'jar', 'wheel_move'):
                        output_file = a[1]
                        break

            result = {
                'success': returncode == 0,
                'stdout': stdout_text,
                'stderr': stderr_text,
                'returncode': returncode,
                'output_file': output_file if (self.tool.get('type') == 'compiler' or self.action == 'package') else None
            }
            show = {
                'success': returncode == 0,
                'returncode': returncode,
                'output_file': output_file if (self.tool.get('type') == 'compiler' or self.action == 'package') else None
            }
            log.info(f"[Main]Compliacion completa: {show}")
            log.debug(f"[Main]Datos de salida de la compilacion: {result.get('stdout'), result.get('stderr')}")
            self.finished.emit(result)

        except Exception as e:
            fail = {
                'success': False,
                'stdout': '',
                'stderr': f'Error al ejecutar el comando: {str(e)}',
                'returncode': -1,
                'output_file': None
            }
            log.info(f"[Main]Compliacion fallida: {fail}")
            self.finished.emit(fail)

    def terminate(self):
        try:
            if self._process and self._process.poll() is None:
                try:
                    self._process.terminate()
                except Exception:
                    pass
        except Exception:
            pass
        super().terminate()

# ========== VENTANA PRINCIPAL ==========
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Compilador/Empaquetador Profesional")
        self.setGeometry(100, 100, 950, 850)

        self.setStyleSheet(STYLE)

        self.compilation_engine = CompilationEngine()
        self.available_tools = []          # Se llenará después de la detección
        self.current_tools = []
        self.current_file = None
        self.selected_tool = None
        self.output_path = None
        self.current_lang_allowed_outputs = []

        self.output_type_map = OUTPUT_TYPE_MAP
        self.worker = None
        self.config = load_config()
        self.detecting_tools = False   # Para evitar detecciones concurrentes

        self.init_ui()

        # Restaurar configuración (sin herramientas aún)
        QTimer.singleShot(0, self.apply_saved_config)

        # Iniciar detección de herramientas en segundo plano
        QTimer.singleShot(200, self.start_tool_detection)

    def init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        self.setCentralWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(12)

        # --- Archivo fuente ---
        file_group = QGroupBox("Archivo fuente")
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Ningún archivo seleccionado")
        self.file_label.setWordWrap(True)
        self.file_button = QPushButton("Seleccionar archivo...")
        self.file_button.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DirOpenIcon', 0)))
        self.file_button.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(self.file_button)
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)

        # --- Información del lenguaje ---
        lang_group = QGroupBox("Información del lenguaje")
        lang_layout = QVBoxLayout()
        self.lang_info_label = QLabel("Lenguaje: -- | Tipo: --")
        self.lang_info_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #4caf50;")
        lang_layout.addWidget(self.lang_info_label)
        lang_group.setLayout(lang_layout)
        main_layout.addWidget(lang_group)

        # --- Herramientas disponibles ---
        tools_group = QGroupBox("Herramientas disponibles")
        tools_layout = QVBoxLayout()
        self.tools_combo = QComboBox()
        self.tools_combo.currentIndexChanged.connect(self.on_tool_selected)
        # Añadir botón en la barra de herramientas o en el layout
        self.project_gen_btn = QPushButton("Generador de Proyectos")
        self.project_gen_btn.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileDialogNewFolder', 0)))
        self.project_gen_btn.clicked.connect(self.open_project_generator)
        tools_layout.addWidget(QLabel("Seleccione una herramienta:"))
        tools_layout.addWidget(self.tools_combo)
        tools_layout.addWidget(self.project_gen_btn)
        self.refresh_tools_btn = QPushButton("Refrescar herramientas")
        self.refresh_tools_btn.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_BrowserReload', 0)))
        self.refresh_tools_btn.clicked.connect(self.refresh_tools)
        tools_layout.addWidget(self.refresh_tools_btn)
        tools_group.setLayout(tools_layout)
        main_layout.addWidget(tools_group)

        # --- Opciones de salida ---
        output_group = QGroupBox("Opciones de salida")
        output_layout = QVBoxLayout()

        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Ruta de salida (opcional, dejar vacío para automático)")
        self.output_browse_btn = QPushButton("Examinar...")
        self.output_browse_btn.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DirOpenIcon', 0)))
        self.output_browse_btn.clicked.connect(self.select_output_path)
        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(self.output_path_edit, 1)
        output_path_layout.addWidget(self.output_browse_btn)
        output_layout.addWidget(QLabel("Archivo de salida:"))
        output_layout.addLayout(output_path_layout)

        output_type_layout = QHBoxLayout()
        self.output_type_label = QLabel("Tipo de salida:")
        self.output_type_combo = QComboBox()
        self.output_type_combo.clear()
        for text in self.output_type_map.keys():
            self.output_type_combo.addItem(text)
        output_type_layout.addWidget(self.output_type_label)
        output_type_layout.addWidget(self.output_type_combo, 1)
        output_type_layout.addStretch()
        output_layout.addLayout(output_type_layout)

        args_layout = QHBoxLayout()
        self.extra_args_edit = QLineEdit()
        self.extra_args_edit.setPlaceholderText("Argumentos adicionales (ej: -O2 -Wall)")
        self.suggest_args_btn = QPushButton("Sugerir")
        self.suggest_args_btn.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileDialogDetailedView', 0)))
        self.suggest_args_btn.clicked.connect(self.show_argument_suggestions)
        args_layout.addWidget(self.extra_args_edit, 1)
        args_layout.addWidget(self.suggest_args_btn)
        output_layout.addWidget(QLabel("Argumentos adicionales:"))
        output_layout.addLayout(args_layout)

        self.release_checkbox = QCheckBox("Build Release (donde aplique)")
        output_layout.addWidget(self.release_checkbox)

        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        # --- Modo de acción ---
        mode_group = QGroupBox("Modo de ejecución")
        mode_layout = QHBoxLayout()
        self.mode_run = QRadioButton("Compilar / Ejecutar (interpretar)")
        self.mode_package = QRadioButton("Empaquetar (generar ejecutable independiente)")
        self.mode_run.setChecked(True)
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.mode_run)
        self.mode_group.addButton(self.mode_package)
        self.mode_run.toggled.connect(self.update_status_label)
        self.mode_package.toggled.connect(self.update_status_label)
        mode_layout.addWidget(self.mode_run)
        mode_layout.addWidget(self.mode_package)
        mode_layout.addStretch()
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)

        self.status_label = QLabel("Modo actual: Compilar / Ejecutar")
        self.status_label.setStyleSheet("background-color: #3a3a3a; padding: 6px; border-radius: 4px; font-weight: bold;")
        main_layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.action_button = QPushButton("Compilar / Ejecutar")
        self.action_button.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_MediaPlay', 0)))
        self.action_button.clicked.connect(self.start_action)
        self.action_button.setEnabled(False)
        self.stop_button = QPushButton("Detener")
        self.stop_button.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_MediaStop', 0)))
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_action)
        self.clear_logs_btn = QPushButton("Limpiar logs")
        self.clear_logs_btn.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_TrashIcon', 0)))
        self.clear_logs_btn.clicked.connect(lambda: self.logs_text.clear())
        btn_layout.addWidget(self.action_button)
        btn_layout.addWidget(self.stop_button)
        btn_layout.addWidget(self.clear_logs_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        logs_group = QGroupBox("Logs y errores")
        logs_layout = QVBoxLayout()
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFontFamily("Courier New")
        self.logs_text.setAcceptRichText(True)
        logs_layout.addWidget(self.logs_text)
        logs_group.setLayout(logs_layout)
        main_layout.addWidget(logs_group)

        self.extra_args_edit.textChanged.connect(self.save_current_config)
        self.output_path_edit.textChanged.connect(self.save_current_config)
        self.release_checkbox.stateChanged.connect(self.save_current_config)

        self.update_tools_list([])

    def open_project_generator(self):
        """Abre el diálogo del generador de proyectos."""
        try:
            from .proyect_editor.project_generator_dialog import ProjectGeneratorDialog
            dialog = ProjectGeneratorDialog(self)
            dialog.show()
        except ImportError as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cargar el generador de proyectos:\n{e}"
            )
            log.error(f"[MainWindow] Error abriendo generador: {e}")

    def show_argument_suggestions(self):
        if not self.selected_tool:
            QMessageBox.information(self, "Sin herramienta", "Primero selecciona una herramienta.")
            return
        tool_name = self.selected_tool.get('name', '')
        if not tool_name:
            return
        args_list = ArgumentSuggester.get_arguments_for_tool(tool_name)
        if not args_list:
            QMessageBox.information(self, "Sin sugerencias", f"No hay argumentos predefinidos para {tool_name}.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Sugerencias para {tool_name}")
        dialog.resize(600, 400)
        layout = QVBoxLayout(dialog)

        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Buscar...")
        layout.addWidget(search_edit)

        list_widget = QListWidget()
        layout.addWidget(list_widget)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Añadir seleccionado")
        close_btn = QPushButton("Cerrar")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        all_items = []
        for arg in args_list:
            item_text = f"{arg['flag']} - {arg['description']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, arg['flag'])
            list_widget.addItem(item)
            all_items.append(item)

        def filter_items():
            search_text = search_edit.text().lower()
            for item in all_items:
                flag = item.data(Qt.UserRole)
                desc = item.text().lower()
                if search_text in flag.lower() or search_text in desc:
                    item.setHidden(False)
                else:
                    item.setHidden(True)

        search_edit.textChanged.connect(filter_items)

        def add_selected():
            current = list_widget.currentItem()
            if current:
                flag = current.data(Qt.UserRole)
                current_args = self.extra_args_edit.text()
                if current_args and not current_args.endswith(' '):
                    self.extra_args_edit.setText(current_args + ' ' + flag)
                else:
                    self.extra_args_edit.setText(current_args + flag)
                dialog.accept()

        add_btn.clicked.connect(add_selected)
        close_btn.clicked.connect(dialog.accept)
        list_widget.itemDoubleClicked.connect(lambda item: add_selected())
        dialog.exec_()

    # ========== DETECCIÓN DE HERRAMIENTAS EN SEGUNDO PLANO ==========
    def start_tool_detection(self):
        if self.detecting_tools:
            return
        self.detecting_tools = True
        self.status_label.setText("Detectando herramientas instaladas...")
        QApplication.processEvents()
        try:
            tools = CompilerDetector.get_all_tools()
            self.on_tools_detected(tools)
        except Exception as e:
            self.append_log(f"Error en detección de herramientas: {e}", kind='warning')
        finally:
            self.detecting_tools = False
            self.status_label.setText("Listo")

    def on_tools_detected(self, tools):
        self.available_tools = tools
        if self.current_file:
            lang_info = LanguageDetector.detect(self.current_file)
            if lang_info:
                self.update_tools_for_language(lang_info)
        else:
            self.update_tools_list([])

    def refresh_tools(self):
        if self.detecting_tools:
            self.append_log("Ya se está detectando herramientas, espera...", kind='warning')
            return
        self.detecting_tools = True
        self.refresh_tools_btn.setEnabled(False)
        self.status_label.setText("Refrescando herramientas...")
        QApplication.processEvents()
        try:
            tools = CompilerDetector.get_all_tools(force_refresh=True)
            self.on_tools_detected(tools)
        except Exception as e:
            self.append_log(f"Error al refrescar herramientas: {e}", kind='warning')
        finally:
            self.detecting_tools = False
            self.refresh_tools_btn.setEnabled(True)
            self.status_label.setText("Listo")

    # ========== MÉTODOS PRINCIPALES ==========
    def apply_saved_config(self):
        cfg = self.config or {}
        last_file = cfg.get('last_file')
        if last_file and os.path.exists(last_file):
            self.current_file = last_file
            self.file_label.setText(last_file)
            lang_info = LanguageDetector.detect(last_file)
            if lang_info:
                self.lang_info_label.setText(f"Lenguaje: {lang_info['language']} | Tipo: {lang_info['type'].capitalize()}")
                self.current_lang_allowed_outputs = lang_info.get('allowed_outputs', [])
                # La actualización de herramientas se hará cuando estén disponibles
                last_tool = cfg.get('last_tool')
                if last_tool and self.available_tools:
                    for i, t in enumerate(self.current_tools):
                        if t.get('name') == last_tool.get('name') and t.get('command') == last_tool.get('command'):
                            self.tools_combo.setCurrentIndex(i)
                            break
        self.extra_args_edit.setText(cfg.get('extra_args', ''))
        self.output_path_edit.setText(cfg.get('output_path', ''))
        self.release_checkbox.setChecked(cfg.get('release_mode', False))

    def update_status_label(self):
        if self.mode_package.isChecked():
            self.status_label.setText("Modo actual: EMPAQUETAR (generar .exe)")
            self.action_button.setText("Empaquetar")
        else:
            self.status_label.setText("Modo actual: Compilar / Ejecutar")
            self.action_button.setText("Compilar / Ejecutar")

    def update_output_types_combo(self, allowed_outputs):
        self.output_type_combo.clear()
        for display_text, output_code in OUTPUT_TYPE_MAP.items():
            if output_code in allowed_outputs:
                self.output_type_combo.addItem(display_text, output_code)
        if self.output_type_combo.count() == 0:
            self.output_type_combo.addItem("(No aplica)", "")

    def update_output_type_ui(self):
        if not self.selected_tool:
            return
        tool_type = self.selected_tool.get('type')
        if tool_type == 'interpreter':
            self.output_type_combo.setEnabled(False)
            self.output_type_combo.clear()
            self.output_type_combo.addItem("(No aplica)", "")
            return
        self.output_type_combo.setEnabled(True)
        allowed = self.current_lang_allowed_outputs.copy()
        tool_capabilities = CompilerDetector.get_tool_output_capabilities(self.selected_tool)
        allowed = [out for out in allowed if out in tool_capabilities]
        if not allowed:
            allowed = tool_capabilities
        self.update_output_types_combo(allowed)

    def _suggest_missing_tools(self, lang_info):
        """Genera mensajes de sugerencia de instalación para herramientas faltantes."""
        ext = lang_info['extension']
        lang_type = lang_info['type']
        suggestions = []

        if lang_type == 'compiler':
            # Herramientas típicas para lenguajes compilados
            if ext in ('.c', '.cpp', '.cc', '.cxx'):
                suggestions.append(CompilerDetector.get_installation_suggestion('gcc'))
                suggestions.append(CompilerDetector.get_installation_suggestion('clang'))
            elif ext == '.java':
                suggestions.append(CompilerDetector.get_installation_suggestion('java'))
            elif ext == '.go':
                suggestions.append(CompilerDetector.get_installation_suggestion('go'))
            elif ext == '.rs':
                suggestions.append(CompilerDetector.get_installation_suggestion('cargo'))
            elif ext == '.cs':
                suggestions.append(CompilerDetector.get_installation_suggestion('dotnet'))
        else:  # interpreter
            if ext == '.py':
                suggestions.append(CompilerDetector.get_installation_suggestion('PyInstaller'))
                suggestions.append(CompilerDetector.get_installation_suggestion('python-build'))
            elif ext == '.js':
                suggestions.append(CompilerDetector.get_installation_suggestion('pkg'))

        # Eliminar duplicados y None
        suggestions = list(dict.fromkeys([s for s in suggestions if s]))
        return suggestions

    def update_tools_for_language(self, lang_info):
        ext = lang_info['extension']
        lang_type = lang_info['type']
        matching = [t for t in self.available_tools if ext in t.get('extensions', [])]
        if lang_type == 'compiler':
            filtered = [t for t in matching if t.get('type') == 'compiler']
        else:
            filtered = [t for t in matching if t.get('type') in ('interpreter', 'packager')]
        self.current_tools = filtered
        self.update_tools_list(filtered)

        if not filtered:
            # No hay herramientas instaladas para este lenguaje
            suggestions = self._suggest_missing_tools(lang_info)
            if suggestions:
                msg = f"No se encontraron herramientas para {lang_info['language']}. Sugerencias de instalación:\n" + "\n".join(f"  • {s}" for s in suggestions)
                self.append_log(msg, kind='warning')
            else:
                self.append_log(f"No se encontraron herramientas para {lang_info['language']}.", kind='warning')
        else:
            # Si hay herramientas, pero quizás falta algún empaquetador específico
            if lang_type == 'interpreter':
                has_packager = any(t.get('type') == 'packager' for t in matching)
                if not has_packager:
                    # Tiene intérprete pero no empaquetador
                    suggestions = self._suggest_missing_tools(lang_info)
                    if suggestions:
                        msg = "Tienes el intérprete instalado, pero no hay empaquetador. Para generar ejecutables instala:\n" + "\n".join(f"  • {s}" for s in suggestions)
                        self.append_log(msg, kind='warning')
                else:
                    self.append_log("✅ Herramienta de empaquetado detectada. Puedes empaquetar este script seleccionando el modo 'Empaquetar'.", kind='info')

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo fuente")
        if file_path:
            self.current_file = file_path
            self.file_label.setText(file_path)
            self.save_current_config(last_file=file_path)

            lang_info = LanguageDetector.detect(file_path)
            if lang_info:
                self.lang_info_label.setText(f"Lenguaje: {lang_info['language']} | Tipo: {lang_info['type'].capitalize()}")
                self.current_lang_allowed_outputs = lang_info.get('allowed_outputs', [])
                self.update_tools_for_language(lang_info)  # ya incluye sugerencias
                self.output_type_combo.setEnabled(False)
                self.output_type_combo.clear()
                self.output_type_combo.addItem("(Selecciona una herramienta)", "")
                self.update_output_type_ui()
            else:
                # Lenguaje desconocido
                self.lang_info_label.setText("Lenguaje: Desconocido | Tipo: --")
                QMessageBox.warning(self, "Advertencia", "No se pudo determinar el lenguaje. Algunas herramientas pueden no funcionar.")
                ext = os.path.splitext(file_path)[1].lower()
                matching = [t for t in self.available_tools if ext in t.get('extensions', [])]
                self.current_tools = matching
                self.update_tools_list(matching)
                self.output_type_combo.setEnabled(False)
                self.mode_package.setEnabled(False)
                self.update_output_types_combo(list(OUTPUT_TYPE_MAP.values()))
                
    def update_tools_list(self, tools):
        self.tools_combo.clear()
        for tool in tools:
            display = f"{tool['name']} ({tool.get('version', 'desconocida')}) - {tool['type'].capitalize()}"
            self.tools_combo.addItem(display, tool)
            idx = self.tools_combo.count() - 1
            tooltip = f"Comando: {tool.get('command')}\nVersión: {tool.get('version','desconocida')}"
            self.tools_combo.setItemData(idx, tooltip, Qt.ToolTipRole)
        self.action_button.setEnabled(len(tools) > 0)
        self.update_mode_buttons()

    def update_mode_buttons(self):
        if self.current_file:
            ext = os.path.splitext(self.current_file)[1].lower()
            has_packager = any(t['type'] == 'packager' and ext in t.get('extensions', []) for t in self.available_tools)
            self.mode_package.setEnabled(has_packager)
            if not has_packager and self.mode_package.isChecked():
                self.mode_run.setChecked(True)
        else:
            self.mode_package.setEnabled(False)
        self.update_status_label()

    def on_tool_selected(self, index):
        if index >= 0:
            self.selected_tool = self.current_tools[index]
            self.save_current_config()
            self.update_output_type_ui()
            self.update_status_label()

    def select_output_path(self):
        file_path = QFileDialog.getExistingDirectory(self, "Guardar archivo de salida")
        if file_path:
            self.output_path_edit.setText(file_path)
            self.output_path = file_path
            self.save_current_config()

    def start_action(self):
        if not self.current_file:
            QMessageBox.warning(self, "Error", "Primero selecciona un archivo fuente.")
            return
        if not self.selected_tool:
            QMessageBox.warning(self, "Error", "Selecciona una herramienta de la lista.")
            return

        output_path = self.output_path_edit.text().strip() or None
        extra_args_str = self.extra_args_edit.text().strip()
        extra_args = extra_args_str.split() if extra_args_str else []
        release_mode = self.release_checkbox.isChecked()
        tool_name = (self.selected_tool.get('name') or '').lower()
        if release_mode and tool_name == 'go':
            extra_args.extend(['-ldflags', '-s -w'])

        output_code = None
        if self.selected_tool.get('type') != 'interpreter':
            output_text = self.output_type_combo.currentText()
            output_code = self.output_type_map.get(output_text, "exe")
            tool_capabilities = CompilerDetector.get_tool_output_capabilities(self.selected_tool)
            if output_code not in tool_capabilities:
                QMessageBox.warning(self, "Incompatibilidad",
                    f"La herramienta {self.selected_tool['name']} no puede generar el tipo de salida '{output_text}'.\n"
                    "Se utilizará el tipo 'Ejecutable (.exe)' por defecto.")
                self.output_type_combo.setCurrentIndex(0)
                output_code = "exe"
        else:
            output_code = None

        if self.mode_package.isChecked() and self.selected_tool.get('type') == 'packager':
            action = 'package'
            self.logs_text.clear()
            self.append_log("=== Preparando empaquetado ===", kind='info')
            self.append_log("Se iniciará el proceso. Revisa la consola para más detalles.", kind='info')
        else:
            action = 'compile'
            self.logs_text.clear()
            self.append_log("=== Preparando compilación/ejecución ===", kind='info')

        self.save_current_config()
        self.action_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.action_button.setText("Procesando...")

        self.worker = CompileWorker(self.compilation_engine, self.current_file,
                                    self.selected_tool, output_path, extra_args,
                                    output_code, release_mode=release_mode)
        if action == 'package':
            self.worker.action = 'package'

        self.worker.line_stdout.connect(lambda s: self.append_log(s, kind='stdout'))
        self.worker.line_stderr.connect(lambda s: self.append_log(s, kind='stderr'))
        self.worker.finished.connect(self.on_action_finished)
        self.worker.start()

    def stop_action(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            try:
                self.worker.terminate()
                self.append_log("Proceso detenido por el usuario.", kind='warning')
            except Exception:
                pass
        self.stop_button.setEnabled(False)

    def append_log(self, text, kind='stdout'):
        safe = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if kind == 'stderr':
            html = f'<div style="color:#b00020;">{safe}</div>'
        elif kind == 'warning':
            html = f'<div style="color:#b06b00;">{safe}</div>'
        elif kind == 'info':
            html = f'<div style="color:#006b6b;">{safe}</div>'
        else:
            html = f'<div>{safe}</div>'
        self.logs_text.append(html)

    def on_action_finished(self, result):
        self.action_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.update_status_label()

        self.append_log("\n=== RESULTADO ===", kind='info')
        if result.get('stdout'):
            self.append_log("=== SALIDA ESTÁNDAR ===", kind='info')
            self.append_log(result.get('stdout'), kind='stdout')
        if result.get('stderr'):
            self.append_log("\n=== ERRORES ===", kind='info')
            tool_name = (self.selected_tool.get('name') or '').lower() if self.selected_tool else ''
            errors = ErrorParser.parse(tool_name, result.get('stderr'))
            for err in errors:
                self.append_log(ErrorParser.format_error(err), kind='stderr')
        else:
            self.append_log("No hubo errores.", kind='info')

        if result.get('success'):
            self.append_log("\n✅ Operación exitosa.", kind='info')
            if result.get('output_file'):
                self.append_log(f"Archivo generado: {result.get('output_file')}", kind='info')
        else:
            self.append_log(f"\n❌ Falló con código de retorno {result.get('returncode')}.", kind='warning')

    def save_current_config(self, last_file=None):
        try:
            cfg = self.config or {}
            if self.selected_tool:
                cfg['last_tool'] = {'name': self.selected_tool.get('name'), 'command': self.selected_tool.get('command')}
            cfg['extra_args'] = self.extra_args_edit.text().strip()
            cfg['output_path'] = self.output_path_edit.text().strip()
            cfg['release_mode'] = bool(self.release_checkbox.isChecked())
            if last_file:
                cfg['last_file'] = last_file
            elif self.current_file:
                cfg['last_file'] = self.current_file
            self.config = cfg
            save_config(cfg)
        except Exception:
            pass

    def closeEvent(self, event):
        self.save_current_config()
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            try:
                self.worker.terminate()
                self.worker.wait(2000)
            except Exception:
                pass
        event.accept()

def main():
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
        window.show()
    except Exception as e:
        log.critical(f"Error critico del sistema: {e}")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
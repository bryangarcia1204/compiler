# src/editor/editor_dialog.py
"""
Diálogo de editor de código independiente.
Permite abrir, editar y guardar cualquier archivo.
"""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QMessageBox, QWidget, QLabel, QLineEdit
)
from PyQt5.QtCore import Qt

from .editor_widget import CodeEditor
from ...utils import logger

log = logger.Logger()


class EditorDialog(QDialog):
    """Ventana independiente para editar código."""

    def __init__(self, parent=None, filepath: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Editor de código - Compilador Profesional")
        self.setGeometry(100, 100, 900, 650)

        self.current_file = filepath
        self.init_ui()

        if filepath and os.path.exists(filepath):
            self.load_file(filepath)

    def init_ui(self):
        """Inicializa la interfaz."""
        main_layout = QVBoxLayout(self)

        # Barra superior
        top_layout = QHBoxLayout()
        self.status_label = QLabel("Archivo: Ninguno")
        top_layout.addWidget(self.status_label)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Ruta del archivo...")
        top_layout.addWidget(self.file_path_edit, 1)

        self.browse_btn = QPushButton("Examinar...")
        self.browse_btn.clicked.connect(self.browse_file)
        top_layout.addWidget(self.browse_btn)

        main_layout.addLayout(top_layout)

        # Editor
        self.editor = CodeEditor(self)
        main_layout.addWidget(self.editor, 1)

        # Botones
        btn_layout = QHBoxLayout()
        self.open_btn = QPushButton("Abrir")
        self.open_btn.clicked.connect(self.browse_file)
        btn_layout.addWidget(self.open_btn)

        self.save_btn = QPushButton("Guardar")
        self.save_btn.clicked.connect(self.save_file)
        btn_layout.addWidget(self.save_btn)

        self.save_as_btn = QPushButton("Guardar como...")
        self.save_as_btn.clicked.connect(self.save_as_file)
        btn_layout.addWidget(self.save_as_btn)

        btn_layout.addStretch()

        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)

        main_layout.addLayout(btn_layout)

    def browse_file(self):
        """Abre diálogo para seleccionar archivo."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo",
            "",
            "Todos los archivos (*.*)"
        )
        if filepath:
            self.load_file(filepath)

    def load_file(self, filepath: str):
        """Carga un archivo en el editor."""
        if self.editor.load_from_file(filepath):
            self.current_file = filepath
            self.status_label.setText(f"Archivo: {os.path.basename(filepath)}")
            self.file_path_edit.setText(filepath)
            log.info(f"[EditorDialog] Archivo cargado: {filepath}")
        else:
            QMessageBox.warning(self, "Error", f"No se pudo cargar el archivo:\n{filepath}")

    def save_file(self):
        """Guarda el archivo actual."""
        if not self.current_file:
            self.save_as_file()
            return

        if self.editor.save_to_file(self.current_file):
            self.status_label.setText(f"Archivo guardado: {os.path.basename(self.current_file)}")
            log.info(f"[EditorDialog] Archivo guardado: {self.current_file}")
        else:
            QMessageBox.warning(self, "Error", "No se pudo guardar el archivo.")

    def save_as_file(self):
        """Guarda el archivo con otro nombre."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar archivo como",
            self.current_file or "",
            "Todos los archivos (*.*)"
        )
        if filepath:
            self.current_file = filepath
            self.file_path_edit.setText(filepath)
            self.save_file()

    def closeEvent(self, event):
        """Verifica si hay cambios sin guardar."""
        if self.editor.is_modified():
            reply = QMessageBox.question(
                self,
                "Cambios sin guardar",
                "Hay cambios sin guardar. ¿Deseas guardarlos?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
        event.accept()
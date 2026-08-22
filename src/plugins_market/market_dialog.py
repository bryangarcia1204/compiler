# src/plugins_market/market_dialog.py
"""
Diálogo del marketplace de plugins.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QTabWidget, QWidget, QTextEdit, QLineEdit,
    QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from typing import Optional
from .plugin_manager import PluginManager
from .plugin_registry import PluginStatus
from ..utils import logger

log = logger.Logger()


class InstallWorker(QThread):
    """Worker para instalar plugins sin bloquear la GUI."""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)

    def __init__(self, manager, plugin_id, version=None):
        super().__init__()
        self.manager = manager
        self.plugin_id = plugin_id
        self.version = version

    def run(self):
        self.progress.emit(f"Instalando {self.plugin_id}...")
        result = self.manager.install_plugin(self.plugin_id, self.version)
        if result:
            # Cargar el plugin después de instalar
            self.manager.load_plugin(self.plugin_id)
        self.finished.emit(result, self.plugin_id)


class MarketDialog(QDialog):
    """Diálogo del marketplace de plugins."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Marketplace de Plugins - Compilador Profesional")
        self.setGeometry(200, 200, 900, 650)

        self.manager = PluginManager()
        self.worker = None

        self.init_ui()
        self.load_plugins()

    def init_ui(self):
        """Inicializa la interfaz."""
        main_layout = QVBoxLayout(self)

        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_market_tab(), "Explorar")
        self.tabs.addTab(self._create_installed_tab(), "Instalados")
        self.tabs.addTab(self._create_create_tab(), "Crear Plugin")
        main_layout.addWidget(self.tabs)

        # ── Botones ──
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refrescar")
        self.refresh_btn.clicked.connect(self.load_plugins)
        btn_layout.addWidget(self.refresh_btn)

        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)

        main_layout.addLayout(btn_layout)

    def _create_market_tab(self) -> QWidget:
        """Crea la pestaña de exploración."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Barra de búsqueda
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar plugins...")
        self.search_edit.textChanged.connect(self._filter_plugins)
        search_layout.addWidget(self.search_edit)

        layout.addLayout(search_layout)

        # Tabla de plugins
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Nombre", "Versión", "Autor", "Lenguajes", "Estado", "Acción"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        return widget

    def _create_installed_tab(self) -> QWidget:
        """Crea la pestaña de plugins instalados."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.installed_list = QListWidget()
        self.installed_list.itemDoubleClicked.connect(self._show_plugin_info)
        layout.addWidget(self.installed_list)

        btn_layout = QHBoxLayout()
        self.uninstall_btn = QPushButton("Desinstalar seleccionado")
        self.uninstall_btn.clicked.connect(self._uninstall_plugin)
        btn_layout.addWidget(self.uninstall_btn)

        self.activate_btn = QPushButton("Activar/Desactivar")
        self.activate_btn.clicked.connect(self._toggle_plugin)
        btn_layout.addWidget(self.activate_btn)

        layout.addLayout(btn_layout)

        return widget

    def _create_create_tab(self) -> QWidget:
        """Crea la pestaña para crear plugins."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Nombre del plugin:"))
        self.plugin_name_edit = QLineEdit()
        layout.addWidget(self.plugin_name_edit)

        layout.addWidget(QLabel("Lenguajes soportados (separados por comas):"))
        self.plugin_langs_edit = QLineEdit()
        self.plugin_langs_edit.setPlaceholderText("python, cpp, rust")
        layout.addWidget(self.plugin_langs_edit)

        layout.addWidget(QLabel("Código del plugin (Python):"))
        self.plugin_code_edit = QTextEdit()
        self.plugin_code_edit.setPlaceholderText("""
from src.compilers.base import CompilerStrategy

class MiPluginStrategy(CompilerStrategy):
    @property
    def tool_name(self):
        return 'mi_plugin'

    @property
    def supported_extensions(self):
        return ['.ext']

    def build_command(self, file_path, output_path=None, extra_args=None,
                      output_type='exe', release_mode=False, target='native'):
        return ['echo', 'Compilando...'], None, []

STRATEGY_CLASS = MiPluginStrategy
""")
        self.plugin_code_edit.setFont(QFont("Consolas", 9))
        layout.addWidget(self.plugin_code_edit)

        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Crear y Instalar Plugin")
        self.create_btn.clicked.connect(self._create_plugin)
        btn_layout.addWidget(self.create_btn)

        layout.addLayout(btn_layout)

        return widget

    def load_plugins(self):
        """Carga la lista de plugins del marketplace."""
        try:
            plugins = self.manager.get_available_plugins()
            self._populate_table(plugins)
            self._populate_installed()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo cargar el marketplace:\n{e}")

    def _populate_table(self, plugins):
        """Llena la tabla con los plugins disponibles."""
        self.table.setRowCount(0)
        self._all_plugins = plugins

        installed_plugins = {p.id: p for p in self.manager.get_installed_plugins()}

        for plugin in plugins:
            row = self.table.rowCount()
            self.table.insertRow(row)

            plugin_id = plugin.get('id', '')
            name = plugin.get('name', plugin_id)
            version = plugin.get('version', '0.0.1')
            author = plugin.get('author', 'Unknown')
            languages = ', '.join(plugin.get('supported_languages', []))

            # Estado
            installed = plugin_id in installed_plugins
            if installed:
                status = "✅ Instalado"
            else:
                status = "📦 Disponible"

            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(version))
            self.table.setItem(row, 2, QTableWidgetItem(author))
            self.table.setItem(row, 3, QTableWidgetItem(languages))
            self.table.setItem(row, 4, QTableWidgetItem(status))

            # Botón de acción
            if installed:
                btn = QPushButton("Desinstalar")
                btn.clicked.connect(lambda checked, pid=plugin_id: self._uninstall_plugin(pid))
            else:
                btn = QPushButton("Instalar")
                btn.clicked.connect(lambda checked, pid=plugin_id: self._install_plugin(pid))

            self.table.setCellWidget(row, 5, btn)

    def _filter_plugins(self, text):
        """Filtra los plugins por texto."""
        text = text.lower()
        for row in range(self.table.rowCount()):
            show = False
            for col in range(4):  # Solo las columnas de texto
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    show = True
                    break
            self.table.setRowHidden(row, not show)

    def _populate_installed(self):
        """Llena la lista de plugins instalados."""
        self.installed_list.clear()

        # Mostrar plugins instalados
        for plugin in self.manager.get_installed_plugins():
            status_map = {
                PluginStatus.ACTIVE: "✅ Activado",
                PluginStatus.INACTIVE: "⏸️ Desactivado",
                PluginStatus.ERROR: "❌ Error",
            }
            # Verificar si realmente está cargado
            loaded = self.manager.is_loaded(plugin.id)
            if loaded and plugin.status != PluginStatus.ACTIVE:
                plugin.status = PluginStatus.ACTIVE
            elif not loaded and plugin.status == PluginStatus.ACTIVE:
                plugin.status = PluginStatus.ERROR
                status = "❌ Error (no cargado)"
            else:
                status = status_map.get(plugin.status, "❓ Desconocido")

            item = QListWidgetItem(f"{plugin.name} ({plugin.version}) - {status}")
            item.setData(Qt.UserRole, plugin.id)
            self.installed_list.addItem(item)

        # Mostrar plugins cargados que no están en el registro
        loaded_ids = self.manager.get_loaded_plugins()
        for plugin_id in loaded_ids:
            if not self.manager.registry.is_installed(plugin_id):
                item = QListWidgetItem(f"{plugin_id} (cargado automáticamente) - ✅ Activado")
                item.setData(Qt.UserRole, plugin_id)
                self.installed_list.addItem(item)

    def _install_plugin(self, plugin_id: str, version: Optional[str] = None):
        """Instala un plugin."""
        reply = QMessageBox.question(
            self,
            "Instalar plugin",
            f"¿Deseas instalar el plugin '{plugin_id}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.worker = InstallWorker(self.manager, plugin_id, version)
        self.worker.finished.connect(self._on_install_finished)
        self.worker.start()

        # Deshabilitar botón temporalmente
        self.setEnabled(False)

    def _on_install_finished(self, success, plugin_id):
        """Maneja la finalización de la instalación."""
        self.setEnabled(True)
        if success:
            QMessageBox.information(self, "Éxito", f"Plugin '{plugin_id}' instalado correctamente.")
            self.load_plugins()
        else:
            QMessageBox.critical(self, "Error", f"No se pudo instalar el plugin '{plugin_id}'.")

    def _uninstall_plugin(self, plugin_id: Optional[str] = None):
        """Desinstala un plugin."""
        if plugin_id is None:
            # Obtener selección
            item = self.installed_list.currentItem()
            if not item:
                QMessageBox.warning(self, "Error", "Selecciona un plugin para desinstalar.")
                return
            plugin_id = item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Desinstalar plugin",
            f"¿Deseas desinstalar el plugin '{plugin_id}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if self.manager.uninstall_plugin(plugin_id):
            QMessageBox.information(self, "Éxito", f"Plugin '{plugin_id}' desinstalado.")
            self.load_plugins()
        else:
            QMessageBox.critical(self, "Error", f"No se pudo desinstalar el plugin '{plugin_id}'.")

    def _toggle_plugin(self):
        """Activa o desactiva un plugin."""
        item = self.installed_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Error", "Selecciona un plugin.")
            return

        plugin_id = item.data(Qt.UserRole)
        plugin = self.manager.registry.get_plugin(plugin_id)
        if not plugin:
            return

        new_state = not plugin.active
        if self.manager.activate_plugin(plugin_id) if new_state else self.manager.deactivate_plugin(plugin_id):
            self._populate_installed()
            self.load_plugins()

    def _show_plugin_info(self, item):
        """Muestra información de un plugin instalado."""
        plugin_id = item.data(Qt.UserRole)
        plugin = self.manager.registry.get_plugin(plugin_id)
        if not plugin:
            return

        QMessageBox.information(
            self,
            f"Información de {plugin.name}",
            f"""
            ID: {plugin.id}
            Nombre: {plugin.name}
            Versión: {plugin.version}
            Autor: {plugin.author}
            Descripción: {plugin.description}
            Lenguajes: {', '.join(plugin.supported_languages)}
            Dependencias: {', '.join(plugin.dependencies) or 'Ninguna'}
            Estado: {'Activo' if plugin.active else 'Inactivo'}
            """
        )

    def _create_plugin(self):
        """Crea e instala un plugin desde el código."""
        name = self.plugin_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Ingresa un nombre para el plugin.")
            return

        code = self.plugin_code_edit.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "Error", "Ingresa el código del plugin.")
            return

        # Guardar plugin temporalmente
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()

            # Instalar
            if self.manager.install_plugin(name):
                QMessageBox.information(self, "Éxito", f"Plugin '{name}' creado e instalado.")
                self.load_plugins()
            else:
                QMessageBox.critical(self, "Error", "No se pudo instalar el plugin.")

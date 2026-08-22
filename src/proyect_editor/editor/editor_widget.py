# src/editor/editor_widget.py
"""
Editor de código avanzado con resaltado de sintaxis.
Basado en QScintilla, soporta múltiples lenguajes.
"""

import os
from PyQt5.Qsci import QsciScintilla, QsciLexerCPP, QsciLexerPython, QsciLexerJavaScript  # type: ignore
from PyQt5.Qsci import QsciLexerMarkdown, QsciLexerJSON, QsciLexerXML, QsciLexerYAML  # type: ignore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QMenu, QAction

from ...utils import logger
log = logger.Logger()


class CodeEditor(QsciScintilla):
    """Editor de código con resaltado de sintaxis y funcionalidades IDE."""

    # Mapeo de extensiones a lexers
    EXTENSION_MAP = {
        '.py': QsciLexerPython,
        '.pyw': QsciLexerPython,
        '.c': QsciLexerCPP,
        '.cpp': QsciLexerCPP,
        '.cc': QsciLexerCPP,
        '.cxx': QsciLexerCPP,
        '.h': QsciLexerCPP,
        '.hpp': QsciLexerCPP,
        '.hxx': QsciLexerCPP,
        '.rs': QsciLexerCPP,  # Rust fallback
        '.go': QsciLexerCPP,  # Go fallback
        '.js': QsciLexerJavaScript,
        '.jsx': QsciLexerJavaScript,
        '.ts': QsciLexerJavaScript,
        '.json': QsciLexerJSON,
        '.xml': QsciLexerXML,
        '.md': QsciLexerMarkdown,
        '.yml': QsciLexerYAML,
        '.yaml': QsciLexerYAML,
        '.toml': QsciLexerYAML,
        '.txt': None,
        '.gitignore': None,
        '': None,
    }

    def __init__(self, parent=None, filename: str = "", content: str = ""):
        super().__init__(parent)
        self.filename = filename
        self.modified = False

        self._setup_editor()
        self._setup_lexer(filename)
        self.setText(content)
        self.textChanged.connect(self._on_text_changed)

    def _setup_editor(self):
        """Configuración básica del editor."""
        # Fuente moderna
        font = QFont("Cascadia Code", 10)
        if not font.exactMatch():
            font = QFont("Consolas", 10)
        font.setFixedPitch(True)
        self.setFont(font)

        # Colores del tema oscuro (similar a VS Code)
        self.bg_color = QColor(0x1e1e1e)
        self.fg_color = QColor(0xd4d4d4)
        self.selection_color = QColor(0x264f78)
        self.line_highlight = QColor(0x2a2a2a)
        self.margin_bg = QColor(0x252526)
        self.margin_fg = QColor(0x858585)

        # Fondo y texto base
        self.setPaper(self.bg_color)
        self.setColor(self.fg_color)
        self.setSelectionBackgroundColor(self.selection_color)

        # Números de línea
        self.setMarginType(0, QsciScintilla.NumberMargin)
        self.setMarginWidth(0, 45)
        self.setMarginsForegroundColor(self.margin_fg)
        self.setMarginsBackgroundColor(self.margin_bg)

        # Línea actual
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(self.line_highlight)

        # Indentación
        self.setIndentationGuides(True)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setIndentationWidth(4)

        # Plegado (folding)
        self.setFolding(QsciScintilla.BoxedFoldStyle)
        self.setFoldMarginColors(self.margin_bg, self.margin_bg)

        # Auto-completado
        self.setAutoCompletionSource(QsciScintilla.AcsAll)
        self.setAutoCompletionThreshold(2)

        # Scrollbars
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Margen para marcadores (si soporta)
        try:
            self.setMarginType(1, QsciScintilla.SymbolMargin)
            self.setMarginWidth(1, 20)
            try:
                self.setMarginSensitivity(1, True)
            except AttributeError:
                pass
        except Exception as e:
            log.debug(f"[CodeEditor] Error configurando margen: {e}")

    def _setup_lexer(self, filename: str):
        """Configura el lexer según la extensión del archivo."""
        ext = os.path.splitext(filename)[1].lower()
        lexer_class = self.EXTENSION_MAP.get(ext)

        if lexer_class:
            try:
                lexer = lexer_class()

                # ── FORZAR COLORES OSCUROS EN EL LEXER ──
                # Establecer el estilo por defecto del lexer para que coincida con el tema oscuro
                lexer.setDefaultPaper(self.bg_color)
                lexer.setDefaultColor(self.fg_color)

                # También configurar el estilo 0 (default) explícitamente
                lexer.setColor(self.fg_color, 0)          # Texto por defecto
                lexer.setPaper(self.bg_color, 0)          # Fondo por defecto

                # Para Python, asegurar que los números y strings sean legibles
                if isinstance(lexer, QsciLexerPython):
                    lexer.setColor(QColor(0x569cd6), QsciLexerPython.Keyword)
                    lexer.setColor(QColor(0xce9178), QsciLexerPython.SingleQuotedString)
                    lexer.setColor(QColor(0xce9178), QsciLexerPython.DoubleQuotedString)
                    lexer.setColor(QColor(0xb5cea8), QsciLexerPython.Number)
                    lexer.setColor(QColor(0x4ec9b0), QsciLexerPython.FunctionMethodName)
                    lexer.setColor(QColor(0x6a9955), QsciLexerPython.Comment)
                    lexer.setColor(QColor(0xc8c8c8), QsciLexerPython.CommentBlock)

                # Para JavaScript
                elif isinstance(lexer, QsciLexerJavaScript):
                    lexer.setColor(QColor(0x569cd6), QsciLexerJavaScript.Keyword)
                    lexer.setColor(QColor(0xce9178), QsciLexerJavaScript.String)
                    lexer.setColor(QColor(0xb5cea8), QsciLexerJavaScript.Number)
                    lexer.setColor(QColor(0x4ec9b0), QsciLexerJavaScript.Function)
                    lexer.setColor(QColor(0x6a9955), QsciLexerJavaScript.Comment)

                # Para C/C++
                elif isinstance(lexer, QsciLexerCPP):
                    lexer.setColor(QColor(0x569cd6), QsciLexerCPP.Keyword)
                    lexer.setColor(QColor(0xce9178), QsciLexerCPP.DoubleQuotedString)
                    lexer.setColor(QColor(0xb5cea8), QsciLexerCPP.Number)
                    lexer.setColor(QColor(0x4ec9b0), QsciLexerCPP.Function)
                    lexer.setColor(QColor(0x6a9955), QsciLexerCPP.Comment)

                # Aplicar el lexer al editor
                self.setLexer(lexer)

                # Forzar actualización del fondo (por si acaso)
                self.setPaper(self.bg_color)

            except Exception as e:
                log.debug(f"[CodeEditor] Error configurando lexer para {ext}: {e}")
                self.setLexer(None)
        else:
            self.setLexer(None)

    def _on_text_changed(self):
        """Marca el archivo como modificado."""
        self.modified = True

    def get_text(self) -> str:
        """Devuelve el contenido del editor."""
        return self.text()

    def set_content(self, content: str):
        """Establece el contenido y reinicia el estado de modificación."""
        self.setText(content)
        self.modified = False

    def is_modified(self) -> bool:
        """Indica si el archivo ha sido modificado."""
        return self.modified or self.isModified()

    def save_to_file(self, filepath: str) -> bool:
        """Guarda el contenido en un archivo."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.get_text())
            self.modified = False
            self.setModified(False)
            return True
        except Exception as e:
            log.error(f"[CodeEditor] Error guardando {filepath}: {e}")
            return False

    def load_from_file(self, filepath: str) -> bool:
        """Carga contenido desde un archivo."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.set_content(f.read())
            self.filename = os.path.basename(filepath)
            self._setup_lexer(filepath)
            return True
        except Exception as e:
            log.error(f"[CodeEditor] Error cargando {filepath}: {e}")
            return False

    def contextMenuEvent(self, event):
        """Menú contextual con opciones de editor."""
        menu = QMenu(self)

        # Acciones de edición
        undo_act = QAction("Deshacer", self)
        undo_act.triggered.connect(self.undo)
        menu.addAction(undo_act)

        redo_act = QAction("Rehacer", self)
        redo_act.triggered.connect(self.redo)
        menu.addAction(redo_act)

        menu.addSeparator()

        cut_act = QAction("Cortar", self)
        cut_act.triggered.connect(self.cut)
        menu.addAction(cut_act)

        copy_act = QAction("Copiar", self)
        copy_act.triggered.connect(self.copy)
        menu.addAction(copy_act)

        paste_act = QAction("Pegar", self)
        paste_act.triggered.connect(self.paste)
        menu.addAction(paste_act)

        menu.addSeparator()

        select_all_act = QAction("Seleccionar todo", self)
        select_all_act.triggered.connect(self.selectAll)
        menu.addAction(select_all_act)

        # Comentar
        if self.lexer():
            comment_act = QAction("Comentar línea", self)
            comment_act.triggered.connect(self._toggle_comment)
            menu.addAction(comment_act)

        menu.exec_(event.globalPos())

    def _toggle_comment(self):
        """Alterna comentario en la línea seleccionada."""
        if self.lexer():
            try:
                line, index = self.getCursorPosition()
                text = self.text(line)
                if text.strip().startswith('#'):
                    self.setSelection(line, 0, line, len(text))
                    self.replaceSelectedText(text.lstrip('# '))
                else:
                    self.setSelection(line, 0, line, len(text))
                    self.replaceSelectedText('# ' + text)
            except Exception as e:
                log.debug(f"[CodeEditor] Error comentando: {e}")

    def goto_line(self, line_number: int):
        """Navega a una línea específica."""
        line_number = max(1, min(line_number, self.lines()))
        self.setCursorPosition(line_number - 1, 0)
        self.ensureLineVisible(line_number - 1)
        self.setFocus()

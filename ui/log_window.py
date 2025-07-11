# ui/log_window.py
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit

class LogWindow(QWidget):
    # --- ИЗМЕНЕНО: Добавляем stylesheet в конструктор ---
    def __init__(self, stylesheet):
        super().__init__()
        
        # --- Применяем стиль ---
        self.setStyleSheet(stylesheet)
        self.setObjectName("logWindow")

        self.setWindowTitle("Лог выполнения")
        self.setGeometry(150, 150, 800, 400)
        layout = QVBoxLayout(self)
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        # Убираем инлайновый стиль, теперь все в QSS
        layout.addWidget(self.log_area)
    
    def add_log(self, message, level):
        # Цвета для темной темы
        color = {"info": "#dcdcdc", "warning": "#fff176", "error": "#e57373", "debug": "#80cbc4"}.get(level, "#dcdcdc")
        self.log_area.appendHtml(f'<span style="color:{color};">{message}</span>')
        level_map = {'error': logging.ERROR, 'warning': logging.WARNING, 'info': logging.INFO}
        logging.log(level_map.get(level, logging.INFO), f"[GUI] {message}")